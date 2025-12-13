from decimal import Decimal

from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator
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
    address = models.ForeignKey(
        'users.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cart_adress',
        verbose_name='Адрес доставки'
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
        on_delete=models.CASCADE,
        verbose_name='Продукт'
    )
    quantity = models.PositiveIntegerField(
        'Количество',
        default=1,
        validators=[MinValueValidator(1)]
    )

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


class OrderCounters(models.Model):
    last_reset_year = models.PositiveBigIntegerField()
    orders_in_year = models.PositiveIntegerField()


class Order(models.Model):
    """Заказ, сформированный из корзины."""

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('done', 'Завершён'),
        ('canceled', 'Отменён'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('sbp', 'СБП'),
        ('cash', 'Наличные курьеру'),
        # ('card', 'Банковская карта'),
        # ('yoomoney', 'ЮMoney'),
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
        related_name='product_orders',
        verbose_name='Продукты'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    total_price = models.DecimalField(
        'Сумма (руб.)',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=Decimal('0.00')
    )
    address = models.ForeignKey(
        'users.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='delivery_orders',
        verbose_name='Адрес доставки'
    )
    comment = models.TextField(
        'Комментарий',
        help_text='Комментарий к заказу',
        null=True,
        blank=True
    )
    delivery = models.DateTimeField(
        'Доставка',
        null=True,
        blank=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='sbp',
        verbose_name='Способ оплаты',
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
        with transaction.atomic():
            counter_obj, _ = (
                OrderCounters.objects.select_for_update().get_or_create(
                    id=1,
                    defaults={'last_reset_year': current_year,
                              'orders_in_year': 0}
                )
            )
            if current_year > counter_obj.last_reset_year:
                counter_obj.orders_in_year = 0
                counter_obj.last_reset_year = current_year
                counter_obj.save()
            OrderCounters.objects.filter(id=1).update(
                orders_in_year=models.F('orders_in_year') + 1
            )
            counter_obj.refresh_from_db()
            return f'{current_year:02d}{str(counter_obj.orders_in_year)}'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        default_related_name = 'orders'
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
        related_name='order_items',
        verbose_name='Продукт'
    )
    quantity = models.PositiveIntegerField('Количество', default=1)
    price = models.DecimalField(
        'Цена',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        validators=[MinValueValidator(0.009)]
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

    def __str__(self):
        return f'{self.product} × {self.quantity}'


class DeliveryRule(models.Model):
    """
    Правило генерации слотов доставки в зависимости от времени создания заказа.
    """

    name = models.CharField('Название правила', max_length=255,)
    time_from = models.TimeField('Начало периода заказа')
    time_to = models.TimeField('Конец периода заказа')
    days_offset = models.PositiveIntegerField('Сдвиг по дням')
    delivery_time_from = models.TimeField('Время начала доставки')
    delivery_time_to = models.TimeField('Время окончания доставки')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    class Meta:
        verbose_name = 'Политика доставки'
        verbose_name_plural = 'Политика доставки'

    def __str__(self):
        return self.name
