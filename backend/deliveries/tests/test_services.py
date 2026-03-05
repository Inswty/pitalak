import pytest
from datetime import datetime, date, time
from django.utils import timezone
from deliveries.services import get_available_delivery_slots


@pytest.mark.django_db
def test_get_available_slots_respects_rule(delivery_rule):
    """Возвращает корректный слот доставки по активному правилу."""

    checkout_time = timezone.make_aware(datetime(2026, 3, 4, 12, 0))
    slots = get_available_delivery_slots(checkout_time)

    assert len(slots) > 0
    slot = slots[0]

    expected_date = date(2026, 3, 6)
    assert slot['date'] == expected_date
    assert slot['time_from'] == time(18, 0)
    assert slot['time_to'] == time(21, 0)
    assert slot['display'] == '06.03 18:00-21:00'
