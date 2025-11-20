from decimal import Decimal
from django.db import transaction

from .models import Order, OrderItem


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
