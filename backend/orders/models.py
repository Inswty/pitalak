from decimal import Decimal

from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.constants import MAX_PRICE_DIGITS, PRICE_DECIMAL_PLACES
from deliveries.models import Delivery
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


class PaymentMethod(models.Model):
    """Способы оплаты."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Методы оплаты'
        verbose_name_plural = 'Методы оплаты'

    def __str__(self):
        return self.name


class Payment(models.Model):
    """Оплата заказа."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        FAILED = 'failed', 'Ошибка'
        REFUNDED = 'refunded', 'Возврат'

    order = models.OneToOneField(
        'Order', on_delete=models.CASCADE, related_name='payment'
    )
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderCounters(models.Model):
    """Хранит счётчики заказов по годам с датой последнего сброса."""

    last_reset_year = models.PositiveSmallIntegerField()
    orders_in_year = models.PositiveIntegerField()


class Order(models.Model):
    """Заказ, сформированный из корзины."""

    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        PROCESSING = 'processing', 'В обработке'
        SHIPPED = 'shipped', 'Отправлен'
        DONE = 'done', 'Завершён'
        CANCELED = 'canceled', 'Отменён'

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
        choices=Status.choices,
        default=Status.NEW
    )
    delivery_price = models.DecimalField(
        'Стоимость доставки (руб.)',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=Decimal('0.00'),
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    items_total = models.DecimalField(
        'Сумма товаров (руб.)',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=Decimal('0.00')
    )
    total_price = models.DecimalField(
        'Итого (руб.)',
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
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Способ оплаты'
    )
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name='orders',
        null=True, blank=True,
        verbose_name='Способ доставки',
    )
    delivery_date = models.DateField('Дата доставки', blank=True, null=True)
    delivery_time_from = models.TimeField('со времени', blank=True, null=True)
    delivery_time_to = models.TimeField('до врмени', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        # Обновляем стоимость доставки и итоговую сумму
        self.delivery_price = (self.delivery.price if self.delivery
                               else Decimal('0.00'))
        self.total_price = self.items_total + self.delivery_price
        super().save(*args, **kwargs)

    def add_product(self, product, quantity, price):
        item, created = OrderItem.objects.get_or_create(
            order=self, product=product,
            defaults={'quantity': quantity, 'price': price}
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=['quantity'])
        self.recalculate_totals()
        return item

    def recalculate_totals(self):
        """Пересчитывает суммы заказа: товары, доставка и итого."""
        self.items_total = sum(
            (item.price * item.quantity for item in self.items.all()),
            start=Decimal('0.00')
        )
        self.delivery_price = (
            self.delivery.price if self.delivery else Decimal('0.00')
        )
        self.total_price = self.items_total + self.delivery_price
        self.save(update_fields=[
            'items_total', 'delivery_price', 'total_price'
        ])

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

    @property
    def payment_status(self):
        if hasattr(self, 'payment'):
            return self.payment.status
        return None

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
    quantity = models.PositiveIntegerField(
        'Количество',
        default=1,
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'Цена',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        validators=[MinValueValidator(0.009)]
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.recalculate_totals()  # Пересчёт суммы при изменении

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.recalculate_totals()  # Пересчёт суммы при удалении

    class Meta:
        verbose_name = 'Позиция в заказе'
        verbose_name_plural = 'Позиции в заказах'

    def __str__(self):
        return f'{self.product} × {self.quantity}'
