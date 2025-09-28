from django.db import models
from django.conf import settings

from core.constants import MAX_PRICE_DIGITS, PRICE_DECIMAL_PLACES
from products.models import Product
from users.models import User


class ShoppingCart(models.Model):
    """Корзина пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Покупатель'
    )
    products = models.ManyToManyField(
        Product,
        through='CartItem',
        related_name='carts',
        verbose_name='Продукты'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'Корзина {self.user}'


class CartItem(models.Model):
    """Товар в корзине."""

    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Позиция в корзине'
        verbose_name_plural = 'Позиции в корзинах'
        constraints = [
            models.UniqueConstraint(
                fields=('cart', 'product'),
                name='unique_product_in_cart'
            )
        ]

    def __str__(self):
        return f'{self.product} × {self.quantity}'


class Order(models.Model):
    """Заказ, сформированный из корзины."""

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('done', 'Завершён'),
        ('canceled', 'Отменён'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    total_price = models.DecimalField(
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-created_at',)

    def __str__(self):
        return f'Заказ # {self.order_number} ({self.user})'


class OrderItem(models.Model):
    """Позиция в заказе."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES
    )

    def __str__(self):
        return f'{self.product} × {self.quantity}'
