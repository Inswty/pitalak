from decimal import Decimal

from orders.models import Order, ShoppingCart


def test_checkout_post_create_order(
        auth_client, user, delivery, payment_method, user_address,
        delivery_rules, cart_with_items, checkout_url, mock_order_send
):
    """Создание заказа из корзины пользователя."""

    # Сумма товаров в корзине
    expected_total = sum(
        item.product.price * item.quantity
        for item in cart_with_items.items.all()
    ) + delivery.price
    # Количество товаров в корзине перед созданием заказа
    expected_count = cart_with_items.items.count()

    # Получаем данные для checkout
    response = auth_client.get(checkout_url)
    # Извлекаем доступный слот доставки
    slot = response.data['delivery_slots'][0]

    payload = {
        "delivery": delivery.id,
        "payment_method": payment_method.id,
        "address": user_address.id,
        "comment": "Angry dog",
        "delivery_date": slot["date"],
        "delivery_time_from": slot["time_from"],
        "delivery_time_to": slot["time_to"],
    }
    # Создаем заказ
    response = auth_client.post(checkout_url, payload, format='json')

    assert response.status_code == 201
    order_id = response.data['order_id']
    order = Order.objects.get(id=order_id)
    assert order.total_price == Decimal(expected_total)
    assert order.items.count() == expected_count
    # Проверка состава заказа
    order_items = order.items.all()
    for cart_item in cart_with_items.items.all():
        assert order_items.filter(
            product=cart_item.product,
            quantity=cart_item.quantity
        ).exists()
    # Проверим что корзина очищена
    cart = ShoppingCart.objects.get(user=user)
    assert cart.items.count() == 0
    # Таск отправки Telegram вызван один раз с правильными параметрами
    mock_order_send.assert_called_once_with(order.order_number,
                                            user.name, user.phone)
