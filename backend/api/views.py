import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    InvalidToken, TokenError, TokenRefreshView
)

from products.models import Category, Product
from users.otp_manager import OTPManager
from users.models import User
from .schemas import (
    category_view_schema, otp_view_set_schemas,
    product_view_schema, token_refresh_schema, user_me_schemas
)
from .serializers import (
    CategorySerializer, CategoryDetailSerializer, OTPRequestSerializer,
    OTPVerifySerializer, ProductListSerializer, ProductDetailSerializer,
    UserSerializer,
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

    queryset = User.objects.prefetch_related('addresses').all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = None
    http_method_names = ['get', 'patch', 'head', 'options']

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
            # Частичное обновление профиля
            serializer = self.get_serializer(user, data=request.data,
                                             partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


@product_view_schema
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only эндпойнт для Product API (list & retrieve)."""

    queryset = (
        Product.objects
        .select_related('category')
        .prefetch_related('images')
    )
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

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


@category_view_schema
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only эндпойнт для Category API (list & retrieve)."""

    permission_classes = (AllowAny,)
    queryset = Category.objects.filter(is_available=True)
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Для retrieve добавляем prefetch
        if self.action == 'retrieve':
            return qs.prefetch_related(
                'products__images',
                'products__category'
            )
        return qs
