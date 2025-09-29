from decimal import Decimal
from django.db import transaction

from .models import Order, OrderItem


class OrderService:
    @classmethod
    @transaction.atomic
    def create_from_cart(cls, cart, address=None):
        """Создать заказ из корзины пользователя."""
        if not cart.items.exists():
            raise ValueError('Невозможно создать заказ из пустой корзины.')
        # выбираем адрес                                                        # подумать тут
        address = cart.user.addresses.filter(is_primary=True).first()
        if not address:
            # берём первый, если основного нет
            address = cart.user.addresses.first()
        # создаём заказ
        order = Order.objects.create(
            user=cart.user,
            address=address,
            status='new',
            total_price=Decimal('0.00'),
        )
        # переносим товары из корзины
        order_items = []
        for item in cart.items.select_related('product'):
            order_items.append(OrderItem(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,  # берём актуальную цену
            ))
        OrderItem.objects.bulk_create(order_items)
        # пересчитываем сумму
        order.update_total_price()
        # очищаем корзину
        cart.items.all().delete()
        return order
