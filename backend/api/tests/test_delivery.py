from datetime import time

from rest_framework import status

from deliveries.models import DeliveryRule


def test_checkout_delivery_slots_structure(
    auth_client, delivery_rule, checkout_url
):
    """Проверка наличия и структуры слотов доставки"""

    response = auth_client.get(checkout_url)

    assert response.status_code == status.HTTP_200_OK
    slots = response.data.get('delivery_slots', [])
    assert len(slots) == 1, 'Слоты не сгенерировались.'
    assert 'date' in slots[0]
    assert 'time_from' in slots[0]
    assert 'time_to' in slots[0]


def test_checkout_delivery_slots_filters_inactive(
    checkout_url, frozen_auth_client
):
    """Проверка фильтрации неактивных правил."""

    # Freeze time '2026-03-04 03:00:00'

    # Создаем активное правило
    DeliveryRule.objects.create(
        name='Активное',
        time_from=time(0, 0), time_to=time(23, 59),
        days_offset=1,
        delivery_time_from=time(10, 0), delivery_time_to=time(12, 0),
        is_active=True
    )
    # Создаем неактивное правило
    DeliveryRule.objects.create(
        name='Выключенное',
        time_from=time(0, 0), time_to=time(23, 59),
        days_offset=1,
        delivery_time_from=time(14, 0), delivery_time_to=time(16, 0),
        is_active=False
    )

    response = frozen_auth_client.get(checkout_url)

    assert response.status_code == status.HTTP_200_OK
    slots = response.data.get('delivery_slots', [])
    assert len(slots) == 1, 'Должен отобразиться только 1 активный слот'
    assert slots == [
        {
            'date': '2026-03-05',
            'time_from': '10:00:00',
            'time_to': '12:00:00',
            'display': '05.03 10:00-12:00'
        }
    ]


def test_checkout_delivery_slots_empty_when_no_matching_rules(
    checkout_url, frozen_auth_client
):
    """Проверка: возвращает пустой список, если подходящих слотов нет."""

    DeliveryRule.objects.create(
        name='Заказ с 10:00 до 18:00',
        time_from=time(10, 0), time_to=time(18, 0),
        days_offset=1,
        delivery_time_from=time(19, 0), delivery_time_to=time(21, 0),
        is_active=True
    )

    response = frozen_auth_client.get(checkout_url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data.get('delivery_slots') == [], (
        'Список слотов должен быть пустым, если время не совпало'
    )
