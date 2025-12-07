from celery import shared_task

from api.services.bot_telegram import send_telegram_message


@shared_task
def send_log_to_telegram(message):
    send_telegram_message(message)
