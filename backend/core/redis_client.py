import logging
from contextlib import contextmanager

from django_redis import get_redis_connection
from redis.exceptions import ConnectionError, RedisError
from rest_framework.exceptions import Throttled

logger = logging.getLogger(__name__)


class RedisClient:
    """Унифицированный клиент для работы с Redis."""

    @staticmethod
    @contextmanager
    def connect():
        """Подключение к Redis с обработкой ошибок."""
        try:
            conn = get_redis_connection('default')
            yield conn
        except (ConnectionError, RedisError) as e:
            logger.error('Redis error: %s', e)
            raise Throttled(detail='Системная ошибка. Попробуйте позже.')
