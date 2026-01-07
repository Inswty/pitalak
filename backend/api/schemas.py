from drf_spectacular.utils import (
    extend_schema, extend_schema_view, inline_serializer
)
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .serializers import (
    OrderDetailSerializer, OrderListSerializer, OTPRequestSerializer,
    OTPVerifySerializer, ProductDetailSerializer, ProductListSerializer,
    ShoppingCartReadSerializer, ShoppingCartWriteSerializer, UserSerializer
)


UNAUTHORIZED_RESPONSE = {
    401: inline_serializer(
        name='UnauthorizedError',
        fields={
            'detail': serializers.CharField(
                default='Учетные данные не были предоставлены.'
            )
        }
    )
}

otp_view_set_schemas = extend_schema_view(
    send=extend_schema(
        operation_id='request_otp',
        summary='Запрос OTP',
        tags=['AUTH'],
        description=(
            'Принимает номер телефона и отправляет SMS с кодом подтверждения.'
        ),
        request=OTPRequestSerializer,
        responses={
            200: inline_serializer(
                name='OTPSendResponse',
                fields={'detail': serializers.CharField(),
                        'TTL': serializers.IntegerField()}
            ),
            429: inline_serializer(
                name='OTPThrottledResponse',
                fields={'detail': serializers.CharField(),
                        'wait': serializers.IntegerField()}
            )
        }
    ),
    verify=extend_schema(
        operation_id='verify_otp',
        summary='Верификация OTP',
        tags=['AUTH'],
        description='Проверяет код и возвращает JWT-токены для авторизации.',
        request=OTPVerifySerializer,
        responses={
            200: inline_serializer(
                name='OTPTokenResponse',
                fields={'access': serializers.CharField(),
                        'refresh': serializers.CharField()
                        }
            ),
            400: inline_serializer(
                name='ValidationError',
                fields={'detail': serializers.CharField()}
            )
        }
    )
)

token_refresh_schema = extend_schema_view(
    post=extend_schema(
        summary='Обновление JWT токена',
        tags=['AUTH'],
        description=(
            'Принимает refresh-токен, возвращает новую пару access/refresh.'),
        request=TokenRefreshSerializer,
        responses={
            200: TokenRefreshSerializer,
            401: inline_serializer(
                name='TokenRefreshError',
                fields={
                    'detail': serializers.CharField(
                        default='Token is invalid or expired'
                    ),
                    'code': serializers.CharField(default='token_not_valid')
                }
            ),
        },
    )
)

user_me_schemas = extend_schema_view(
    me=[
        # Настройка для GET
        extend_schema(
            methods=['GET'],
            operation_id='get_my_profile',
            summary='Получить профиль /me/',
            tags=['USERS'],
            responses={200: UserSerializer, **UNAUTHORIZED_RESPONSE}
        ),
        # Настройка для PATCH
        extend_schema(
            methods=['PATCH'],
            operation_id='update_my_profile',
            summary='Изменить профиль /me/',
            tags=['USERS'],
            responses={200: UserSerializer, **UNAUTHORIZED_RESPONSE}
        ),
    ]
)

category_view_schema = extend_schema_view(
    list=extend_schema(
        operation_id='list_categories',
        summary='Список категорий',
        tags=['CATALOG'],
        description='Возвращает список всех активных категорий.',
    ),
    retrieve=extend_schema(
        operation_id='get_category_details',
        summary='Детали категории',
        tags=['CATALOG'],
        description='Возвращает полную информацию о конкретной категории.',
    ),
)

product_view_schema = extend_schema_view(
    list=extend_schema(
        operation_id='list_products',
        summary='Список товаров',
        tags=['CATALOG'],
        description=(
            'Получение полного списка товаров с фильтрацией по категориям.'
        ),
        responses={200: ProductListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        operation_id='get_product_details',
        summary='Детали товара',
        tags=['CATALOG'],
        description='Получение подробной информации о товаре по его ID.',
        responses={200: ProductDetailSerializer},
    )
)

cart_view_schema = extend_schema_view(
    me=[
        extend_schema(
            methods=['GET'],
            operation_id='get_cart',
            summary='Получить корзину пользователя',
            tags=['CART'],
            description='Возвращает товары в корзине текущего пользователя.',
            responses={
                200: ShoppingCartReadSerializer,
                **UNAUTHORIZED_RESPONSE
            },
        ),
        extend_schema(
            methods=['PATCH'],
            operation_id='update_cart',
            summary='Обновить корзину пользователя',
            tags=['CART'],
            description='Обновляет товары в корзине.',
            request=ShoppingCartWriteSerializer,
            responses={
                200: ShoppingCartReadSerializer,
                **UNAUTHORIZED_RESPONSE
            },
        ),
        extend_schema(
            methods=['DELETE'],
            operation_id='clear_cart',
            summary='Очистить корзину пользователя',
            tags=['CART'],
            description='Удаляет все товары из корзины текущего пользователя.',
            responses={204: None, **UNAUTHORIZED_RESPONSE},
        ),
    ]
)

order_view_schema = extend_schema_view(
    list=extend_schema(
        methods=['GET'],
        operation_id='list_orders',
        summary='Список заказов текущего пользователя',
        tags=['ORDER'],
        description='Возвращает список заказов текущего пользователя.',
        responses={
            200: OrderListSerializer(many=True),
            **UNAUTHORIZED_RESPONSE
        }
    ),
    retrieve=extend_schema(
        methods=['GET'],
        operation_id='retrieve_order',
        summary='Получить детали заказа',
        tags=['ORDER'],
        description=(
            'Возвращает детальную информацию о конкретном заказе'
            'пользователя, включая товары и адрес доставки.'
        ),
        responses={200: OrderDetailSerializer, **UNAUTHORIZED_RESPONSE}
    ),
)
