import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from api.services.sms_provider import TargetSMSClient

SMS_BALANCE_CACHE_KEY = 'sms_provider_balance'

logger = logging.getLogger(__name__)


@shared_task(bind=False)
def send_otp_sms_task(phone: str, otp: str):
    """Задача Celery для асинхронной отправки OTP."""

    if settings.DEBUG:
        logger.info('DEV MODE: Отправка SMS пропущена для %s', phone)
        return 'dev_mode_skipped'
    # Production: Отправка через внешний сервис
    try:
        client = TargetSMSClient()
        message_id = client.send_sms(phone, otp)

        if message_id is None:
            # Если отправка не удалась, логируем и завершаем задачу.
            logger.error(
                f'Ошибка провайдера при отправке OTP на {phone}.'
            )
            return None
        else:
            logger.info(
                'SMS успешно отправлено на %s. Инвалидация кеша OTP-баланса.',
                phone
            )
            cache.delete(SMS_BALANCE_CACHE_KEY)
            logger.info('Кеш OTP-баланса очищен.')
            return message_id
    except Exception as exc:
        logger.error(
            f'Критическая ошибка Celery при отправке OTP на {phone}: {exc}'
        )
        raise exc
