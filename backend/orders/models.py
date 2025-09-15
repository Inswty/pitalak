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
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_carts',
        verbose_name='Продукт'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'product'),
                name='unique_product_in_user'
            ),
        )

    def __str__(self):
        return f'{self.user} → {self.product} ({self.quantity})'


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
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    total_price = models.DecimalField(
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=0.00
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ #{self.id} ({self.user})'


class OrderItem(models.Model):
    """Связь заказа и продуктов (многие-ко-многим)."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(  # цена на момент покупки
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES
    )

    def __str__(self):
        return f'{self.product} x {self.quantity}'
