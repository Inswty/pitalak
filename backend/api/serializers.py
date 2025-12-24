from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField

from products.models import Category, Ingredient, Product, ProductImage
from users.models import Address, User


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

    pass


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
    """
    Переопределяет стандартный UserCreateSerializer, ограничивает
    поля только полем 'phone'.
    """
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('phone',)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            'id', 'locality', 'street', 'house', 'flat', 'floor', 'is_primary'
        )


class UserSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ('phone', 'name', 'last_name', 'email', 'addresses')

    def validate_phone(self, value):
        if self.instance and self.instance.phone != value:
            raise serializers.ValidationError(
                'Изменение номера телефона запрещено.'
            )
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        # Извлекаем данные адресов из пришедшего запроса
        addresses_data = validated_data.pop('addresses', None)
        # Обновляем основные поля пользователя
        instance = super().update(instance, validated_data)
        # Если адреса переданы, обновляем их
        if addresses_data is not None:
            instance.addresses.all().delete()
            for address_data in addresses_data:
                Address.objects.create(user=instance, **address_data)
        return instance


class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage
        fields = ('image',)


class IngredientInProductSerializer(serializers.ModelSerializer):
    amount_per_100g = serializers.DecimalField(max_digits=6, decimal_places=2,
                                               read_only=True)

    class Meta:
        model = Ingredient
        fields = (
            'name', 'proteins', 'fats', 'carbs', 'energy_value',
            'amount_per_100g'
        )


class BaseProductSerializer(serializers.ModelSerializer):

    category = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'category', 'description', 'images', 'weight',
            'price',
        )


class ProductListSerializer(BaseProductSerializer):

    class Meta(BaseProductSerializer.Meta):
        pass


class ProductDetailSerializer(BaseProductSerializer):

    ingredients = serializers.SerializerMethodField()
    nutrients = serializers.SerializerMethodField()

    class Meta(BaseProductSerializer.Meta):
        fields = BaseProductSerializer.Meta.fields + (
            'proteins', 'fats', 'carbs', 'energy_value', 'ingredients',
            'nutrients',
        )

    def to_representation(self, instance):
        """Убирает PFC из ответа если nutrition_mode==none."""
        data = super().to_representation(instance)
        nutrition_mode = getattr(instance, 'nutrition_mode', None)
        if nutrition_mode == 'none':
            for field in ('proteins', 'fats', 'carbs', 'energy_value'):
                data.pop(field, None)
        return data

    def get_ingredients(self, obj):
        """
        Возвращает ингредиенты продукта с указанием их количества.
        """
        result = []
        # .all() использует данные из prefetch
        for link in obj.product_ingredients.all():
            ingredient = link.ingredient
            result.append({
                'name': ingredient.name,
                'amount_per_100g': link.amount_per_100g,
            })
        return result

    def get_nutrients(self, obj):
        """
        Возвращает агрегированные нутриенты ингредиентов продукта.
        """
        links = obj.product_ingredients.all()
        if not links:
            return []
        total_weight = sum(Decimal(link.amount_per_100g) for link in links)
        if total_weight == 0:
            return []
        nutrients = {}

        for link in links:
            ingredient = link.ingredient
            # Доля ингредиента в продукте
            ratio = Decimal(link.amount_per_100g) / total_weight
            # nutrient_links уже в памяти благодаря prefetch_related
            for n_link in ingredient.nutrient_links.all():
                nutrient = n_link.nutrient
                key = nutrient.id

                if key not in nutrients:
                    nutrients[key] = {
                        'name': nutrient.name,
                        'amount_per_100g': n_link.amount_per_100g * ratio,
                        'measurement_unit': nutrient.measurement_unit,
                        'rda': nutrient.rda,
                    }
                else:
                    nutrients[key]['amount_per_100g'] += (
                        n_link.amount_per_100g * ratio
                    )
        for nutrient in nutrients.values():
            nutrient['amount_per_100g'] = nutrient['amount_per_100g'].quantize(
                Decimal('0.001'),
                rounding=ROUND_HALF_UP
            )
        return list(nutrients.values())


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('name', 'slug')


class CategoryDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')
