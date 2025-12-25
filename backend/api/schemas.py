from drf_spectacular.utils import (
    extend_schema, extend_schema_view, inline_serializer
)
from rest_framework import serializers

from .serializers import (
    OTPRequestSerializer, OTPVerifySerializer, UserSerializer
)


otp_view_set_schemas = extend_schema_view(
    send=extend_schema(
        operation_id='request_otp',
        summary='Запрос OTP',
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
        description='Проверяет код и возвращает JWT-токены для авторизации.',
        request=OTPVerifySerializer,
        responses={
            200: inline_serializer(
                name='OTPTokenResponse',
                fields={'refresh': serializers.CharField(),
                        'access': serializers.CharField()}
            ),
            400: inline_serializer(
                name='ValidationError',
                fields={'detail': serializers.CharField()}
            )
        }
    )
)

user_me_schemas = extend_schema_view(
    me=[
        # Настройка для GET
        extend_schema(
            methods=['GET'],
            operation_id='get_my_profile',
            summary='Получить профиль /me/',
            responses={200: UserSerializer}
        ),
        # Настройка для PATCH
        extend_schema(
            methods=['PATCH'],
            operation_id='update_my_profile',
            summary='Изменить профиль /me/',
            responses={200: UserSerializer}
        ),
    ]
)

category_view_schema = extend_schema_view(
    list=extend_schema(
        operation_id='list_categories',
        summary='Список категорий',
        description='Возвращает список всех активных категорий.',
    ),
    retrieve=extend_schema(
        operation_id='get_category_details',
        summary='Детали категории',
        description='Возвращает полную информацию о конкретной категории.',
    ),
)

product_view_schema = extend_schema_view(
    list=extend_schema(
        operation_id='list_products',
        summary='Список товаров',
        description=(
            'Получение полного списка товаров с фильтрацией по категориям.'
        )
    ),
    retrieve=extend_schema(
        operation_id='get_product_details',
        summary='Детали товара',
        description='Получение подробной информации о товаре по его ID.'
    )
)
