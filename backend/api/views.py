from decimal import Decimal
import json
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    InvalidToken, TokenError, TokenRefreshView
)

from core.redis_client import RedisClient
from deliveries.models import Delivery
from orders.models import Order, PaymentMethod, ShoppingCart
from orders.services import OrderService
from products.models import Category, Product
from users.otp_manager import OTPManager
from users.models import Address, User
from .schemas import (
    address_schemas, cart_view_schema, category_view_schema,
    checkout_view_schema, order_view_schema, otp_view_set_schemas,
    product_view_schema, token_refresh_schema, user_me_schemas
)
from .serializers import (
    AddressSerializer, CategorySerializer, CategoryDetailSerializer,
    CheckoutReadSerializer, CheckoutWriteSerializer, OrderDetailSerializer,
    OrderListSerializer, OTPRequestSerializer, OTPVerifySerializer,
    ProductListSerializer, ProductDetailSerializer, ShoppingCartReadSerializer,
    ShoppingCartWriteSerializer, UserSerializer
)

logger = logging.getLogger(__name__)


@otp_view_set_schemas
class OTPViewSet(viewsets.ViewSet):
    """Эндпоинт для запроса/верификации OTP."""

    permission_classes = (AllowAny,)
    authentication_classes = []

    @action(detail=False, methods=['post'])
    def send(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        # Отправка SMS
        try:
            otp = OTPManager.request_otp(phone)
        except Throttled as e:
            # Вернем 429 с wait
            return Response(
                {'detail': e.detail, 'wait': e.wait},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except Exception as e:
            # Ловим ошибки, не связанные с Redis
            logger.error('Критическая ошибка менеджера OTP: %s', e)
            raise ValidationError({'detail': 'Не удалось отправить OTP'})
        if settings.DEBUG:
            # Отображаем OTP только в режиме разработки
            print(f'DEV MODE: OTP на номер {phone}: {otp}')
            logger.debug(f'DEV MODE: OTP на номер {phone}: {otp}')

        logger.info('Запрос на отправку OTP принят для %s', phone)
        return Response({
            'detail': 'OTP запрошен. Проверьте ваш телефон.',
            'TTL': settings.OTP_TTL_SECONDS
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp = serializer.validated_data['otp']

        is_valid, message = OTPManager.verify_otp(phone, otp)
        if not is_valid:
            raise ValidationError({'detail': message})

        user = self._get_or_create_user(phone)
        token = self._generate_token(user)
        if token:
            logger.info(
                'JWT Access: сгенерирован и будет отпрален токен для %s',
                phone
            )
        return Response(token, status=status.HTTP_200_OK)

    def _get_or_create_user(self, phone: str):
        """Создание нового пользователя или получение существующего."""
        user, created = User.objects.get_or_create(phone=phone)
        if created:
            logger.info('Создан новый пользователь %s', phone)
        else:
            logger.info('Пользователь %s найден в базе', phone)
        return user

    def _generate_token(self, user):
        """Генерация JWT-токенов (refresh и access)."""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


@token_refresh_schema
class LoggedTokenRefreshView(TokenRefreshView):
    """Логирование обновления Refresh-токена"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        raw_refresh = request.data.get('refresh')

        if response.status_code == 200:
            try:
                token = RefreshToken(raw_refresh)
                user_id = token.get('user_id')
                logger.info(
                    'JWT Refresh: успешное обновление токена для пользователя '
                    'с user_id: %s',
                    user_id
                )
            except (InvalidToken, TokenError):
                # Ошибка уже есть в response
                user_id = "unknown"
            except Exception as e:
                # Если случилось непонятное
                logger.debug(
                    'Ошибка при попытке парсинга токена для логов: %s', e
                )
        else:
            logger.warning(
                'JWT Refresh: Попытка обновления с невалидным токеном. IP: %s',
                self.get_client_ip(request)
            )
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


@user_me_schemas
class UserViewSet(viewsets.GenericViewSet):
    """ViewSet для работы с профилем текущего пользователя."""

    permission_classes = (IsAuthenticated,)
    queryset = User.objects.prefetch_related('addresses').all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']
    pagination_class = None

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """
        Эндпоинт /api/users/me/
        Позволяет получить или отредактировать профиль текущего юзера.
        """
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            """Обновляет профиль пользователя и логирует изменённые поля."""
            old_data = self.get_serializer(user).data

            serializer = self.get_serializer(
                user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            new_data = serializer.data
            changes = {
                field: {
                    'from': old_data[field],
                    'to': new_data.get(field),
                }
                for field in request.data
                if field in old_data and old_data[field] != new_data.get(field)
            }
            if changes:
                user_info = (
                    f'ID: {user.id} | '
                    f'Phone: {getattr(user, "phone", "N/A")} | '
                    f'Name: {getattr(user, "name", "N/A")}'
                )
                log_message = json.dumps(
                    changes, ensure_ascii=False, indent=2
                )
                logger.info(
                    f'Профиль пользователя обновлён: '
                    f'({user_info}):\n{log_message}'
                )
            return Response(new_data)


@address_schemas
class AddressViewSet(viewsets.ModelViewSet):
    """Адреса пользователя."""

    permission_classes = (IsAuthenticated,)
    serializer_class = AddressSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@product_view_schema
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only эндпойнт для Product API (list & retrieve)."""

    permission_classes = (AllowAny,)
    queryset = (
        Product.objects
        .select_related('category')
        .prefetch_related('images')
    )

    def get_queryset(self):
        qs = super().get_queryset()
        category_slug = self.request.query_params.get('category')
        if category_slug:
            # Фильтр по слагу категории
            qs = qs.filter(category__slug=category_slug)
        if self.action == 'retrieve':
            return qs.prefetch_related(
                'product_ingredients__ingredient__nutrient_links__nutrient'
            )
        return qs.filter(is_available=True).order_by('id')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer


@category_view_schema
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only эндпойнт для Category API (list & retrieve)."""

    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(is_available=True).order_by('name')
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        # Для retrieve добавляем prefetch
        if self.action == 'retrieve':
            return qs.prefetch_related(
                'products__images',
                'products__category'
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer


@cart_view_schema
class CartViewSet(viewsets.GenericViewSet):
    """Корзина покупок пользователя."""

    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        """Возвращаем корзину только для текущего пользователя."""
        return ShoppingCart.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ('me',):
            if self.request.method in ('PATCH',):
                return ShoppingCartWriteSerializer
        return ShoppingCartReadSerializer

    @action(detail=False, methods=['get', 'patch', 'delete'], url_path='me')
    def me(self, request):
        """Эндпоинт /cart/me/ для текущего пользователя"""
        cart, _ = ShoppingCart.objects.get_or_create(user=request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(cart)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            write_serializer = self.get_serializer(
                cart,
                data=request.data
            )
            write_serializer.is_valid(raise_exception=True)
            write_serializer.save()
            read_serializer = ShoppingCartReadSerializer(cart)
            return Response(read_serializer.data)

        elif request.method == 'DELETE':
            cart.items.all().delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


@order_view_schema
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Эндпойнт заказов текущего пользователя."""

    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Возвращаем заказы только текущего пользователя."""
        return (
            Order.objects.filter(user=self.request.user)
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        return OrderListSerializer


@checkout_view_schema
class CheckoutViewSet(viewsets.GenericViewSet):
    """Энтпойнт для оформления заказа (checkout)."""

    permission_classes = (IsAuthenticated,)
    pagination_class = None

    def get_serializer_class(self):
        return (
            CheckoutWriteSerializer
            if self.action == 'create'
            else CheckoutReadSerializer
        )

    def get_cart(self):
        cart, _ = ShoppingCart.objects.prefetch_related(
            'items__product'
        ).get_or_create(user=self.request.user)

        return cart

    def list(self, request, *args, **kwargs):
        """Получение данных для checkout."""
        cart = self.get_cart()
        user = self.request.user

        subtotal = sum(
            item.product.price * item.quantity
            for item in cart.items.all()
        )

        checkout_started_at = timezone.now()
        with RedisClient.connect() as conn:
            conn.setex(
                f'checkout:{user.id}', settings.CHECKOUT_TTL_SECONDS,
                checkout_started_at.isoformat()
            )
            logger.info(
                'Redis: сохранен checkout_started_at для пользователя: '
                '%s (id=%s), TTL: %s сек', user.phone, user.id,
                settings.CHECKOUT_TTL_SECONDS
            )
        slots = OrderService.get_available_delivery_slots(
            checkout_started_at
        )

        deliveries = Delivery.objects.filter(is_active=True)
        payment_methods = PaymentMethod.objects.filter(is_active=True)

        serializer = self.get_serializer({
            'checkout_started_at': checkout_started_at,
            'items': cart.items.all(),
            'deliveries': deliveries,
            'delivery_slots': slots,
            'payment_methods': payment_methods,
            'subtotal': subtotal,
            'delivery_price': Decimal('0.00'),
        })

        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Обрабатывает оформление заказа (checkout)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = OrderService.create_order_for_checkout(
                request.user, serializer.validated_data
            )
        except ValueError as e:  # Ловим ValueError из сервиса
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
                'order_id': order.id,
                'order_number': order.order_number,
                'total': order.total_price,
                'delivery': order.delivery.name,
                'delivery_time_to': (
                    order.delivery_time_from.strftime('%H:%M')
                    if order.delivery_time_from else None
                ),
                'delivery_time_from': (
                    order.delivery_time_to.strftime('%H:%M')
                    if order.delivery_time_to else None
                ),
            },
            status=status.HTTP_201_CREATED
        )
