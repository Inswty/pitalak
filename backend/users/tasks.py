import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from api.services.sms_provider import TargetSMSClient, TelegramClient

SMS_BALANCE_CACHE_KEY = 'sms_provider_balance'

logger = logging.getLogger(__name__)


@shared_task(bind=False)
def send_otp_sms_task(phone: str, otp: str) -> str | None:
    """Асинхронная отправка OTP через Telegram или SMS fallback."""

    if settings.DEBUG:
        logger.info('DEV MODE: Отправка SMS пропущена для %s', phone)
        return 'dev_mode'

    tg_client = TelegramClient()

    # 1. Telegram: prepare
    request_id = tg_client.prepare_send(phone)

    if request_id:
        logger.info(
            'Telegram доступен для %s, request_id=%s',
            phone,
            request_id,
        )

        message_id = tg_client.send_sms(
            phone=phone,
            otp=otp,
            request_id=request_id,
        )

        if message_id:
            logger.info(
                'OTP отправка через Telegram для %s, message_id=%s',
                phone,
                message_id,
            )
            return message_id

        logger.warning(
            'Telegram неудачная отправка на %s, fallback to SMS',
            phone,
        )

    # 2. Fallback — TargetSMS
    sms_client = TargetSMSClient()
    sms_message_id = sms_client.send_sms(phone, otp)

    if sms_message_id:
        logger.info(
            'OTP отправка через SMS для %s, message_id=%s',
            phone,
            sms_message_id,
        )
        cache.delete(SMS_BALANCE_CACHE_KEY)
        return sms_message_id

    logger.error(
        'OTP неудачная отправка на %s, ничего не получилось!',
        phone,
    )
    return None
