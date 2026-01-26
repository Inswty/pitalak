from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from djoser.serializers import UserCreateSerializer
from drf_spectacular.utils import extend_schema_field
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from core.constants import MAX_PRICE_DIGITS, PRICE_DECIMAL_PLACES
from orders.models import (
    CartItem, Delivery, Order, OrderItem, PaymentMethod, ShoppingCart,
)
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
    Переопределяет стандартный UserCreateSerializer.
    Ограничивает поля только полем 'phone'.
    """
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('phone',)


class AddressSerializer(serializers.ModelSerializer):
    """Сериализатор адреса пользователя."""

    class Meta:
        model = Address
        fields = (
            'id', 'locality', 'street', 'house', 'flat', 'floor', 'is_primary'
        )


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя с привязанными адресами."""

    addresses = AddressSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'phone', 'name', 'last_name', 'email', 'addresses')

    def validate_phone(self, value):
        if self.instance and self.instance.phone != value:
            raise serializers.ValidationError(
                'Изменение номера телефона запрещено.'
            )
        return value

    def validate_addresses(self, value):
        if not value:
            return value
        primary_count = sum(
            1 for address in value
            if address.get('is_primary', False)
        )
        if primary_count > 1:
            raise serializers.ValidationError(
                'Только один адрес может быть основным.'
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
    """Сериализатор изображения продукта."""

    class Meta:
        model = ProductImage
        fields = ('image',)


class IngredientInProductSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиента с нутриентами на 100 г продукта."""

    amount_per_100g = serializers.DecimalField(max_digits=6, decimal_places=2,
                                               read_only=True)

    class Meta:
        model = Ingredient
        fields = (
            'name', 'proteins', 'fats', 'carbs', 'energy_value',
            'amount_per_100g'
        )


class BaseProductSerializer(serializers.ModelSerializer):
    """Базовый сериализатор продукта."""

    category = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'category', 'description', 'images', 'weight',
            'price',
        )


class ProductListSerializer(BaseProductSerializer):
    """Сериализатор продукта для списка."""

    class Meta(BaseProductSerializer.Meta):
        pass


class ProductDetailSerializer(BaseProductSerializer):
    """Детальный сериализатор продукта с ингредиентами и нутриентами."""

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

    @extend_schema_field({  # OpenAPI-схема для поля SerializerMethodField
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "amount_per_100g": {"type": "number", "format": "decimal"},
            },
            "required": ["name", "amount_per_100g"]
        }
    })
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

    @extend_schema_field({  # OpenAPI-схема для поля SerializerMethodField
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "amount_per_100g": {"type": "number", "format": "decimal"},
                "measurement_unit": {"type": "string"},
                "rda": {"type": "number", "nullable": True},
            },
            "required": ["name", "amount_per_100g", "measurement_unit"]
        }
    })
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
    """Сериализатор категории."""

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор категории."""

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class CartItemSerializer(serializers.ModelSerializer):
    """Сериализатор товаров в корзине пользователя."""

    id = serializers.IntegerField(read_only=True, default=0)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)
    price = serializers.DecimalField(
        source='product.price', max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES, read_only=True
    )
    summ = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product_id', 'name', 'price', 'quantity', 'summ')

    def get_summ(self, obj):
        return obj.product.price * obj.quantity


class ShoppingCartReadSerializer(serializers.ModelSerializer):
    """Сериализатор корзины покупок пользователя - чтение."""

    items = CartItemSerializer(source='items.all', many=True, read_only=True)
    items_total = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingCart
        fields = ('items', 'items_total')

    def get_items_total(self, obj):
        return sum(
            item.product.price * item.quantity for item in obj.items.all()
        )


class CartItemWriteSerializer(serializers.Serializer):
    """Сериализатор для записи позиции в корзину."""

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'
    )
    quantity = serializers.IntegerField(min_value=1)


class ShoppingCartWriteSerializer(serializers.Serializer):

    items = CartItemWriteSerializer(many=True)

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.get('items', [])
        instance.items.all().delete()
        CartItem.objects.bulk_create([
            CartItem(
                cart=instance,
                product=item['product'],
                quantity=item['quantity']
            )
            for item in items_data
        ])
        return instance


class DeliverySerializer(serializers.ModelSerializer):
    """Сериализатор для доставки."""

    class Meta:
        model = Delivery
        fields = ('id', 'name', 'price', 'description')


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Сериализатор для метода оплаты."""

    class Meta:
        model = PaymentMethod
        fields = ('id', 'name')


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор товаров в заказе пользователя."""

    product_id = serializers.IntegerField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ('product_id', 'name', 'quantity', 'price',)


class OrderListSerializer(serializers.ModelSerializer):
    """Сериализатор заказов пользователя."""

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'status', 'created_at', 'delivery',
            'items_total',
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    """Сериализатор Detail-заказа пользователя."""

    delivery = serializers.SlugRelatedField(read_only=True, slug_field='name')
    delivery_address = AddressSerializer(source='address', read_only=True)
    payment_method = serializers.SlugRelatedField(read_only=True,
                                                  slug_field='name')
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'status', 'comment', 'created_at',
            'delivery', 'delivery_address', 'items_total', 'delivery_price',
            'total_price', 'payment_method', 'items',
        )


class CheckoutReadSerializer(serializers.Serializer):
    """Сериализатор для оформления заказа (checkout), чтение."""

    addresses = AddressSerializer(many=True)
    items = CartItemSerializer(many=True)

    deliveries = DeliverySerializer(many=True)
    payment_methods = PaymentMethodSerializer(many=True)

    subtotal = serializers.DecimalField(
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES
    )


class CheckoutWriteSerializer(serializers.Serializer):
    delivery = serializers.PrimaryKeyRelatedField(
        queryset=Delivery.objects.filter(is_active=True)
    )
    payment_method = serializers.PrimaryKeyRelatedField(
        queryset=PaymentMethod.objects.filter(is_active=True)
    )
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all()
    )
    comment = serializers.CharField(required=False, allow_blank=True)
    """
    delivery_date = serializers.DateField()
    delivery_time_from = serializers.TimeField(required=False, allow_null=True)
    delivery_time_to = serializers.TimeField(required=False, allow_null=True)
    """
    """
    def validate(self, data):
        if data.get('delivery_time_from') and data.get('delivery_time_to'):
            if data['delivery_time_from'] > data['delivery_time_to']:
                raise serializers.ValidationError(
                    "Время 'с' не может быть больше времени 'до'.")
        return data
    """
