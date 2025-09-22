import logging
from django.conf import settings
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField

from users.models import User

logger = logging.getLogger(__name__)  # --- ??? ---


class BaseOTPSerializer(serializers.Serializer):
    """Базовый сериализатор для OTP."""

    phone = PhoneNumberField(
        region='RU',
        error_messages={
            'invalid': 'Некорректный номер телефона',
            'blank': 'Номер телефона обязателен для заполнения'
        }
    )

    def validate_phone(self, value):
        phone_str = value.as_e164.lstrip('+')
        return phone_str


class OTPRequestSerializer(BaseOTPSerializer):
    """Сериализатор для запроса отправки OTP на номер телефона."""

    pass  # используется только phone из BaseOTPSerializer


class OTPVerifySerializer(BaseOTPSerializer):
    """Сериализатор для верификации OTP."""

    otp = serializers.CharField(
        min_length=settings.OTP_LENGTH,
        max_length=settings.OTP_LENGTH,
        error_messages={
            'min_length': f'OTP должен содержать {settings.OTP_LENGTH} цифр.',
            'max_length': f'OTP должен содержать {settings.OTP_LENGTH} цифр.',
            'blank': 'OTP обязателен для заполнения.',
        }
    )

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                'OTP должен содержать только цифры.'
            )
        return value


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('phone',)
