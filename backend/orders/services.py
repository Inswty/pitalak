from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from .models import DeliveryRule, Order, OrderItem


class OrderService:
    """Сервис для работы с заказами."""

    @classmethod
    @transaction.atomic
    def create_from_cart(cls, cart):
        """Создаёт новый заказ на основе корзины пользователя."""
        if not cart.items.exists():
            raise ValueError('Невозможно создать заказ из пустой корзины.')
        # Используем адрес из корзины
        if not cart.address:
            raise ValueError('В корзине не выбран адрес. '
                             'Добавьте адрес перед оформлением заказа.')
        # Создаём заказ
        order = Order.objects.create(
            user=cart.user,
            address=cart.address,
            status='new',
            total_price=Decimal('0.00'),
        )
        # Формируем список объектов OrderItem
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,  # Актуальная цена
            )
            for item in cart.items.select_related('product')
        ]

        # Сохраняем все позиции одним запросом
        OrderItem.objects.bulk_create(order_items)
        # Пересчитываем сумму
        order.total_price = sum(
            item.price * item.quantity for item in order_items
        )
        order.save(update_fields=['total_price'])
        # Очищаем корзину
        cart.items.all().delete()
        return order

    @classmethod
    def get_available_delivery_slots(cls, order_created_at):
        """
        Возвращает список доступных слотов доставки, сгенерированных на основе
        активных правил и времени создания заказа.
        """
        rules = DeliveryRule.objects.filter(is_active=True)

        slots = []
        order_time = order_created_at.time()

        for rule in rules:
            if rule.time_from <= order_time <= rule.time_to:
                date = (
                    order_created_at + timedelta(days=rule.days_offset)
                ).date()

                slots.append({
                    'date': date,
                    'time_from': rule.delivery_time_from,
                    'time_to': rule.delivery_time_to,
                    'display': f'{date.strftime('%d.%m')} '
                               f'{rule.delivery_time_from.strftime('%H:%M')}-'
                               f'{rule.delivery_time_to.strftime('%H:%M')}'
                })

        return slots
