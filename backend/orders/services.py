from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from .models import (
    DeliveryRule, Order, OrderItem, Payment, ShoppingCart,
)


class OrderService:
    """Сервис для работы с заказами."""

    @classmethod
    @transaction.atomic
    def create_from_cart(cls, cart, *, order_data=None):
        """Создаёт новый заказ на основе корзины пользователя."""
        if not cart.items.exists():
            raise ValueError('Невозможно создать заказ из пустой корзины.')

        order_data = order_data or {}
        # Получаем объект Delivery из order_data, если он передан
        delivery = order_data.get('delivery')
        delivery_price = delivery.price if delivery else Decimal('0.00')
        items_total = sum(
            item.product.price * item.quantity for item in cart.items.all()
        )
        total_price = items_total + delivery_price
        # Создаём заказ
        order = Order.objects.create(
            user=cart.user,
            status=Order.Status.NEW,
            delivery_price=delivery_price,
            items_total=items_total,
            total_price=total_price,
            **order_data,
        )
        # Формируем список объектов OrderItem
        order_items = [
            OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )
            for item in cart.items.select_related('product')
        ]
        # Сохраняем все позиции одним запросом
        OrderItem.objects.bulk_create(order_items)
        # Очищаем корзину
        cart.items.all().delete()
        return order

    @classmethod
    def create_order_for_checkout(cls, user, validated_data):
        """Создаёт заказ для оформления (checkout)."""
        cart = ShoppingCart.objects.get(user=user)
        order = cls.create_from_cart(
            cart,
            order_data={
                'delivery': validated_data['delivery'],
                'address': validated_data['address'],
                'comment': validated_data.get('comment'),
                'payment_method': validated_data.get('payment_method'),
            }
        )
        # Создаём объект оплаты
        Payment.objects.create(
            order=order,
            method=validated_data['payment_method'],
            amount=order.total_price,
            status=Payment.Status.PENDING
        )
        # Меняем статус заказа
        order.status = Order.Status.PROCESSING
        order.save(update_fields=['status'])
        return order

    @classmethod
    def get_available_delivery_slots(cls, checkout_started_at):
        """
        Возвращает список доступных слотов доставки, сгенерированных на основе
        активных правил и текущего времени.
        """
        rules = DeliveryRule.objects.filter(is_active=True)
        slots = []
        for rule in rules:
            if rule.time_from <= checkout_started_at.time() <= rule.time_to:
                delivery_date = (
                    checkout_started_at.date()
                    + timedelta(days=rule.days_offset)
                )
                slots.append({
                    'date': delivery_date,
                    'time_from': rule.delivery_time_from,
                    'time_to': rule.delivery_time_to,
                    'display': (
                        f'{delivery_date.strftime("%d.%m")} '
                        f'{rule.delivery_time_from.strftime("%H:%M")}-'
                        f'{rule.delivery_time_to.strftime("%H:%M")}'
                    ),
                })
        return slots
