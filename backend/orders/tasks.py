from celery import shared_task

from api.services.bot_telegram import send_telegram_message


@shared_task
def send_order_created_message(order_id, name, phone):
    send_telegram_message(f'Новый заказ # {order_id}\n[{name}, {phone}]')
