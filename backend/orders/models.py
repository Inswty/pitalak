from decimal import Decimal

from django.db import models
from django.conf import settings
from django.utils import timezone

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

    order_number = models.CharField(
        'Номер заказа', max_length=10, unique=True, editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Заказчик'
    )
    products = models.ManyToManyField(
        Product,
        through='OrderItem',
        related_name='orders',
        verbose_name='Продукты'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    total_price = models.DecimalField(
        'Сумма',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=Decimal('0.00')
    )
    address = models.ForeignKey(
        'users.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name='Адрес доставки'
    )

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def add_product(self, product, quantity, price):
        item, created = OrderItem.objects.get_or_create(
            order=self, product=product,
            defaults={'quantity': quantity, 'price': price}
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=['quantity'])
        self.update_total_price()
        return item

    def update_total_price(self):
        self.total_price = sum(
            (item.price * item.quantity for item in self.items.all()),
            start=Decimal('0.00')
        )
        self.save(update_fields=['total_price'])

    def generate_order_number(self):
        current_year = timezone.now().year % 100
        last_order = Order.objects.filter(
            order_number__startswith=f'{current_year}'
        ).order_by('id').last()
        if last_order:
            last_number = int(last_order.order_number[2:])
        else:
            last_number = 0
        return f'{current_year}{last_number + 1}'

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_total_price()  # пересчёт суммы при изменении

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total_price()  # пересчёт суммы при удалении

    class Meta:
        verbose_name = 'Позиция в заказе'
        verbose_name_plural = 'Позиции в заказах'
        constraints = [
            models.UniqueConstraint(
                fields=('order', 'product'),
                name='unique_product_in_order'
            )
        ]

    def __str__(self):
        return f'{self.product} × {self.quantity}'
