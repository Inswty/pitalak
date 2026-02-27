import pytest
from django.urls import reverse

from deliveries.models import Delivery, DeliveryRule
from orders.models import CartItem, PaymentMethod, ShoppingCart
from products.models import Category, Product
from users.models import Address


@pytest.fixture
def mock_order_send(mocker):
    """
    Фикстура для перехвата отправки уведомлений.
    Возвращает объект мока, чтобы в тестах можно было проверить вызов.
    """
    return mocker.patch('orders.signals.send_order_created_message.delay')


# =================================
# Content fixtures
# =================================
@pytest.fixture
def category(db):
    return Category.objects.create(name='Категория_1')


@pytest.fixture
def products(category):
    return [
        Product.objects.create(
            category=category,
            name='Товар1',
            price=100
        ),
        Product.objects.create(
            category=category,
            name='Товар2',
            price=200)
    ]


@pytest.fixture
def shopping_cart(db, user):
    return ShoppingCart.objects.create(user=user)


@pytest.fixture
def cart_with_items(shopping_cart, products):
    for product in products:
        CartItem.objects.create(
            cart=shopping_cart,
            product=product,
        )
    return shopping_cart


@pytest.fixture
def user_address(user):
    return Address.objects.create(
        user=user,
        locality='Бобруйск',
        street='Ромашковая',
        house='88',
        flat='5',
        floor='1'
    )


@pytest.fixture
def delivery():
    return Delivery.objects.create(
        name='Катапульта',
        description='Airways',
        price=500
    )


@pytest.fixture
def delivery_rules(db):
    return DeliveryRule.objects.create(
        name='Заказ с 00:00 до 23:59',
        time_from='00:00',
        time_to='23:59',
        days_offset=2,
        delivery_time_from='18:00',
        delivery_time_to='21:00',
    )


@pytest.fixture
def payment_method():
    return PaymentMethod.objects.create(name='OnlinePayment')


# =================================
# URL fixtures
# =================================
@pytest.fixture
def checkout_url():
    return reverse('api:checkout-list')


@pytest.fixture
def address_url():
    return reverse('api:addresses-list')


@pytest.fixture
def users_me_url():
    return reverse('api:users-me')


@pytest.fixture
def token_refresh():
    return reverse('api:token_refresh')
