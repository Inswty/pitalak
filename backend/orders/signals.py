import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order
from .tasks import send_order_created_message

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def order_created(sender, instance, created, **kwargs):
    """
    Обрабатывает событие создания заказа
    и отправляет уведомление в Telegram.
    """
    logger.info('Создан заказ, запуск отправки сообщения в телеграм')
    if created:
        send_order_created_message.delay(
            instance.order_number,
            instance.user.name,
            str(instance.user.phone)
        )
