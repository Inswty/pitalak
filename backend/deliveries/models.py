from decimal import Decimal

from django.db import models

from core.constants import MAX_PRICE_DIGITS, PRICE_DECIMAL_PLACES


class Delivery(models.Model):
    """Варианты доставки."""

    name = models.CharField('Название', max_length=100)
    price = models.DecimalField(
        'Стоимость (руб.)',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=Decimal('0.00')
    )
    description = models.TextField('Описание')
    requires_delivery_slot = models.BooleanField('Требуется выбор даты',
                                                 default=True)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Варианты доставки'
        verbose_name_plural = 'Варианты доставки'

    def __str__(self):
        return self.name


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
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Политика доставки'
        verbose_name_plural = 'Политика доставки'

    def __str__(self):
        return self.name
