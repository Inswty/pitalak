from datetime import timedelta

from deliveries.models import DeliveryRule


def get_available_delivery_slots(checkout_started_at):
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
    return sorted(slots, key=lambda s: (s['date'], s['time_from']))
