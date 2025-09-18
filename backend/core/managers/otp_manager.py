import logging
import secrets
import string

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class OTPManager:
    """Менеджер для работы с OTP."""

    @staticmethod
    def generate_otp():
        """Безопасная генерация OTP"""
        opt = ''.join(
            secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH)
        )
        logger.debug('Сгенерирован OTP: %s', opt)
        return opt

    @staticmethod
    def get_cache_key(phone):
        return f'otp_{phone}'

    @staticmethod
    def save_otp(phone, otp):
        cache_key = OTPManager.get_cache_key(phone)
        cache_data = {
            'otp': otp,
            'attempts': 0,
            'created_at': now().isoformat()
        }

        cache.set(cache_key, cache_data, timeout=settings.OTP_TTL_SECONDS)
        logger.info(
            'OTP сохранен для телефона: %s, TTL: %s сек, attempts: 0',
            phone, settings.OTP_TTL_SECONDS
        )
        logger.debug('Данные OTP: %s', cache_data)

    @staticmethod
    def verify_otp(phone, user_otp):
        cache_key = OTPManager.get_cache_key(phone)
        data = cache.get(cache_key)

        if not data:
            logger.warning(
                'Попытка верификации OTP для %s: OTP не найден или истек',
                phone
            )
            return False, 'OTP не найден или истек'
        # Логируем текущее состояние
        logger.debug(
            'Верификация OTP для %s: attempts=%s, created_at=%s',
            phone, data['attempts'], data['created_at']
        )

        if data['attempts'] >= settings.MAX_OTP_ATTEMPTS:
            cache.delete(cache_key)
            logger.warning(
                'Превышено количество попыток для телефона %s. OTP удален.',
                phone
            )
            return False, 'Превышено количество попыток'
        data['attempts'] += 1
        cache.set(cache_key, data, timeout=settings.OTP_TTL_SECONDS)
        logger.info(
            'Попытка верификации #%s для телефона %s',
            data['attempts'], phone
        )
        # Безопасное сравнение
        if secrets.compare_digest(str(data['otp']), str(user_otp)):
            cache.delete(cache_key)
            logger.info(
                'Успешная верификация OTP для телефона %s',
                phone
            )
            return True, 'Успешно'
        logger.warning(
            'Неверный OTP для телефона %s. Осталось попыток: %s',
            phone, settings.MAX_OTP_ATTEMPTS - data['attempts']
        )
        return False, 'Неверный OTP'
