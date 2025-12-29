import logging
import secrets
import string
from typing import Tuple
from contextlib import contextmanager

from django.conf import settings
from django_redis import get_redis_connection
from redis.exceptions import ConnectionError, RedisError
from rest_framework.exceptions import Throttled

from users.tasks import send_otp_sms_task


logger = logging.getLogger(__name__)


class OTPManager:
    """Унифицированный менеджер для работы с OTP и ограничениями."""

    @staticmethod
    @contextmanager
    def redis_conn():
        conn = get_redis_connection('default')
        try:
            yield conn
        except (ConnectionError, RedisError) as e:
            logger.error('Redis error: %s', e)
            raise Throttled(detail='Системная ошибка. Попробуйте позже.')

    @staticmethod
    def generate_otp() -> str:
        otp = ''.join(
            secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH)
        )
        logger.info('Сгенерирован OTP: %s', otp)
        return otp

    # Ключи для Redis
    @classmethod
    def _get_keys(cls, phone):
        return {
            'otp': f'otp_{phone}',
            'rate': f'otp_rate_{phone}',
            'cooldown': f'otp_last_request_{phone}',
        }

    @classmethod
    def can_send_otp(cls, phone):
        """Проверка лимита и кулдауна."""
        keys = cls._get_keys(phone)
        with cls.redis_conn() as conn:
            # Атомарно проверяем оба условия
            pipe = conn.pipeline()
            pipe.get(keys['rate'])
            pipe.ttl(keys['rate'])
            pipe.ttl(keys['cooldown'])
            count, rate_ttl, cooldown_ttl = pipe.execute()
            count = int(count or 0)
            # Hourly rate
            if count >= settings.MAX_OTP_REQUESTS_PER_HOUR:
                minutes = (rate_ttl + 59) // 60
                logger.warning('Превышен лимит OTP для %s, '
                               'блокировка на %s мин.', phone, minutes)
                raise Throttled(
                    wait=rate_ttl,
                    detail=f'Превышен лимит запросов. '
                    f'Попробуйте через {minutes} минут.'
                )
            # Cooldown
            if cooldown_ttl > 0:
                logger.warning(
                    'Кулдаун активен для %s, '
                    'осталось %s сек.', phone, cooldown_ttl
                )
                raise Throttled(
                    wait=cooldown_ttl,
                    detail=f'Подождите {cooldown_ttl} секунд '
                    f'перед следующим запросом.'
                )

    @classmethod
    def register_otp_request(cls, phone: str) -> None:
        """Регистрирует отправку OTP (увеличивает счетчики)."""
        keys = cls._get_keys(phone)
        with cls.redis_conn() as conn:
            # Безопасно создаем ключ с TTL, если его нет,
            # Иначе просто увеличиваем
            if not conn.set(keys['rate'], 1, ex=3600, nx=True):
                conn.incr(keys['rate'])
            conn.set(keys['cooldown'], 1, ex=settings.OTP_COOLDOWN_SECONDS)

    @classmethod
    def save_otp(cls, phone: str, otp: str) -> None:
        """Сохраняет OTP в Redis."""
        keys = cls._get_keys(phone)
        with cls.redis_conn() as conn:
            try:
                conn.hset(keys['otp'], mapping={'otp': otp, 'attempts': '0'})
                conn.expire(keys['otp'], settings.OTP_TTL_SECONDS)
                logger.info('OTP сохранен для телефона: %s, TTL: %s сек',
                            phone, settings.OTP_TTL_SECONDS)
            except (ConnectionError, RedisError) as e:
                logger.error('Ошибка сохранения OTP для %s: %s', phone, e)
                raise

    @classmethod
    def verify_otp(cls, phone: str, user_otp: str) -> Tuple[bool, str]:
        """Верификация OTP с учетом количества попыток."""
        keys = cls._get_keys(phone)
        with cls.redis_conn() as conn:
            try:
                if not conn.exists(keys['otp']):
                    logger.warning('OTP не найден или истек для телефона %s',
                                   phone)
                    return False, 'OTP не найден или истек'
                # Атомарно увеличиваем attempts и получаем его новое значение
                attempts = conn.hincrby(keys['otp'], 'attempts', 1)
                stored_otp = conn.hget(keys['otp'], 'otp')
                if not stored_otp:
                    logger.error('Некорректные данные OTP для %s', phone)
                    return False, 'Системная ошибка'
                # Проверяем OTP
                if secrets.compare_digest(stored_otp.decode(), user_otp):
                    conn.delete(keys['otp'])
                    logger.info('Успешная верификация OTP для телефона %s',
                                phone)
                    return True, 'Успешно'
                # После неудачной попытки
                remaining_attempts = settings.MAX_OTP_ATTEMPTS - attempts
                if remaining_attempts == 0:
                    # Это была последняя попытка - удаляем OTP
                    conn.delete(keys['otp'])
                    return False, 'Превышено количество попыток'
                logger.warning('Неверный OTP для %s. Осталось попыток: %s',
                               phone, remaining_attempts)
                return (False, f'Неверный OTP. Осталось попыток: '
                        f'{remaining_attempts}')
            except (ConnectionError, RedisError) as e:
                logger.error('Ошибка верификации OTP для %s: %s', phone, e)
                return False, 'Системная ошибка'

    @classmethod
    def request_otp(cls, phone: str) -> str:
        """
        Полный процесс запроса OTP с проверкой лимитов
        и асинхронной отправкой.
        """
        # 1. Проверка лимитов
        cls.can_send_otp(phone)
        # 2. Генерация и сохранение
        otp = OTPManager.generate_otp()
        cls.register_otp_request(phone)
        cls.save_otp(phone, otp)
        # 3. Отправка (асинхронная)
        send_otp_sms_task.delay(phone.as_e164, otp)
        return otp  # Возвращаем OTP для логирования в DEV
