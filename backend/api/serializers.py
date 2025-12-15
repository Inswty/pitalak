import logging
from django.conf import settings
from djoser.serializers import UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField

from products.models import Ingredient, Nutrient, Product, ProductImage
from users.models import User

logger = logging.getLogger(__name__)                                    # --- ??? ---


class BaseOTPSerializer(serializers.Serializer):
    """Базовый сериализатор для OTP."""

    phone = PhoneNumberField(
        region='RU',
        error_messages={
            'invalid': 'Некорректный номер телефона',
            'blank': 'Номер телефона обязателен для заполнения'
        }
    )


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


class ProductImageSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = ProductImage
        fields = ('image',)


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('name',)


class BaseProductSerializer(serializers.ModelSerializer):

    category = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'category', 'images', 'weight',
            'price',
        )


class ProductListSerializer(BaseProductSerializer):

    class Meta(BaseProductSerializer.Meta):
        pass


class ProductDetailSerializer(BaseProductSerializer):

    ingredients = IngredientSerializer(many=True, read_only=True)

    class Meta(BaseProductSerializer.Meta):
        fields = BaseProductSerializer.Meta.fields + (
            'ingredients', 'proteins', 'fats', 'carbs', 'energy_value',
        )
