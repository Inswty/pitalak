from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .serializers import OTPRequestSerializer, OTPVerifySerializer


OTP_SEND_SCHEMA = extend_schema(
    summary="Запрос на отправку OTP",
    description=(
        "Принимает номер телефона и отправляет SMS с кодом подтверждения."
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
)

OTP_VERIFY_SCHEMA = extend_schema(
    summary="Верификация кода",
    description="Проверяет код и возвращает JWT-токены для авторизации.",
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
