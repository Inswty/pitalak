import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.test import APIClient

from backend.core.redis_client import RedisClient

User = get_user_model()


def pytest_sessionstart(session):
    """
    Проверка доступности Redis перед стартом тестов.
    """
    try:
        # Пытаемся подключиться и пингануть
        with RedisClient.connect() as conn:
            conn.ping()
    except Exception as e:
        # Если Редис лежит — рубим всё сразу
        pytest.exit(
            '\n' + '=' * 50
            + f'\n[ОШИБКА] Redis не доступен: {e}\n'
            '\nДля работы тестов нужен запущенный Redis-сервер.'
            '\nПодсказка: docker run -d -p 6379:6379 redis'
            '\nили локально: \\Redis-x64-5.0.14.1\\redis-server.exe'
            '\n' + '=' * 50 + '\n',
            returncode=1
        )


# =================================
# User fixtures
# =================================
@pytest.fixture
def user(db):
    """Тестовый пользователь."""
    return User.objects.create_user(phone='+79001234567', name='Pytester')


@pytest.fixture
def auth_client(user):
    """
    Клиент с JWT авторизацией.
    Генерируем токен напрямую, без POST /send-otp/ и /verify-otp/.
    """
    client = APIClient()
    # Генерируем JWT
    token = str(AccessToken.for_user(user))
    # Передаём токен в заголовок
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client
