from rest_framework import status

from orders.models import Order, ShoppingCart


def test_checkout_get_schema(auth_client, checkout_url):
    """GET checkout возвращает корректные поля."""

    response = auth_client.get(checkout_url)
    expected_keys = {
        'checkout_started_at',
        'items', 'deliveries',
        'delivery_slots',
        'payment_methods',
        'subtotal'
    }
    assert response.status_code == status.HTTP_200_OK
    assert expected_keys.issubset(response.data.keys())


def test_checkout_delivery_slots_structure(
    auth_client, delivery_rules, checkout_url
):
    """Проверка наличия и структуры слотов доставки"""

    response = auth_client.get(checkout_url)
    assert response.status_code == status.HTTP_200_OK
    slots = response.data.get('delivery_slots', [])
    assert len(slots) > 0, 'Слоты не сгенерировались.'
    assert 'date' in slots[0]
    assert 'time_from' in slots[0]
    assert 'time_to' in slots[0]


def test_checkout_post_create_order(
    auth_client, user, delivery, payment_method, user_address,
    delivery_rules, cart_with_items, checkout_url, mock_order_send
):
    """Создание заказа из корзины пользователя."""

    # Количество товаров в корзине перед созданием заказа
    expected_count = cart_with_items.items.count()
    # Сохраняем состав корзины до очистки
    cart_items_snapshot = list(cart_with_items.items.all())

    # Сумма товаров в корзине
    expected_total = sum(
        item.product.price * item.quantity
        for item in cart_items_snapshot
    ) + delivery.price

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

    assert response.status_code == status.HTTP_201_CREATED
    order_id = response.data['order_id']
    order = Order.objects.get(id=order_id)
    assert order.total_price == expected_total
    assert order.items.count() == expected_count

    # Проверка состава заказа
    expected_map = {
        item.product_id: (item.quantity, item.product.price)
        for item in cart_items_snapshot
    }
    actual_map = {
        item.product_id: (item.quantity, item.price)
        for item in order.items.all()
    }
    assert actual_map == expected_map

    # Проверим что корзина очищена
    cart = ShoppingCart.objects.get(user=user)
    assert cart.items.count() == 0
    # Таск отправки Telegram вызван один раз с правильными параметрами
    mock_order_send.assert_called_once_with(order.order_number,
                                            user.name, user.phone)
