import logging

from celery import shared_task
from django.conf import settings

from api.services.sms_provider import TargetSMSClient

logger = logging.getLogger(__name__)


# Используем bind=True для доступа к self.retry()
@shared_task(bind=True)
def send_otp_sms_task(self, phone: str, otp: str):
    """Задача Celery для асинхронной отправки OTP."""
    client = TargetSMSClient()

    if settings.DEBUG:
        logger.info('DEV MODE: Отправка SMS пропущена для %s', phone)
        return 'dev_mode_skipped'

    # Production: Отправка через внешний сервис
    try:
        message_id = client.send_sms(phone, otp)

        if message_id is None:
            # Если отправка не удалась, инициируем повторную попытку Celery
            logger.warning(
                f'Ошибка провайдера при отправке OTP на {phone}.'
                ' Повторная попытка.'
            )
            raise self.retry()

    except Exception as exc:
        # Обработка других ошибок
        logger.error(
            f'Критическая ошибка Celery при отправке OTP на {phone}: {exc}'
        )
        # Повторить задачу с учетом настроек
        # CELERY_TASK_RETRY_DELAY и MAX_RETRIES
        raise self.retry(exc=exc)
