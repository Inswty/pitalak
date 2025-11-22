from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from .models import DeliveryRule, Order, OrderItem


class OrderService:
    @classmethod
    @transaction.atomic
    def create_from_cart(cls, cart):
        """Создать заказ из корзины пользователя."""
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
        # Переносим товары из корзины
        order_items = []
        for item in cart.items.select_related('product'):
            order_items.append(OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,  # Актуальная цена
            ))
        OrderItem.objects.bulk_create(order_items)
        # Пересчитываем сумму
        order.update_total_price()
        # Очищаем корзину
        cart.items.all().delete()
        return order


def get_available_delivery_slots(order_created_at):
    """
    Возвращает список доступных слотов доставки, сгенерированных на основе
    активных правил и времени создания заказа.
    """
    rules = DeliveryRule.objects.filter(is_active=True)

    slots = []
    order_time = order_created_at.time()

    for rule in rules:
        if rule.time_from <= order_time <= rule.time_to:
            date = (order_created_at + timedelta(days=rule.days_offset)).date()

            slots.append({
                'date': date,
                'time_from': rule.delivery_time_from,
                'time_to': rule.delivery_time_to,
                'display': f'{date.strftime("%d.%m")} '
                           f'{rule.delivery_time_from.strftime("%H:%M")}-'
                           f'{rule.delivery_time_to.strftime("%H:%M")}'
            })

    return slots
