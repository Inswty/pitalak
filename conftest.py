import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.test import APIClient


from backend.core.redis_client import RedisClient
from backend.users.otp_manager import OTPManager


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
            '\n' + '=' * 50 + '\n',
            returncode=1
        )


@pytest.fixture
def mock_send_sms(mocker):
    """Мок для асинхронной отправки OTP через Celery."""
    return mocker.patch('users.tasks.send_otp_sms_task.delay')


@pytest.fixture(autouse=True)
def mock_sms_balance(mocker):
    """Подменяем метод получения баланса во всех тестах."""

    mock_instance = mocker.patch(
        'admin_extensions.context_processors.TargetSMSClient'
    ).return_value
    mock_instance.get_balance.return_value = (
        {'money': {'value': '999.99', 'currency': 'RUR'}}
    )
    return mock_instance


@pytest.fixture
def redis_client():
    """Фикстура Redis с очисткой до и после теста."""
    with RedisClient.connect() as client:
        # Очищаем Redis перед тестом
        client.flushdb()
        yield client
        # Очищаем Redis после теста
        client.flushdb()


@pytest.fixture
def auth_otp_flow(
    client, otp_send_url, otp_verify_url, redis_client, mock_send_sms
):
    """Фикстура-фабрика: возвращает функцию полного цикла OTP-авторизации."""
    def _flow(phone: str):
        # Запрашиваем код
        send_res = client.post(otp_send_url, {"phone": phone}, format='json')
        assert send_res.status_code == status.HTTP_200_OK, \
            f'Ошибка при отправке OTP: {send_res.data}'

        # Достаем код из Redis через менеджер
        keys = OTPManager._get_keys(phone)
        otp_data = redis_client.hgetall(keys['otp'])

        correct_code = otp_data.get(b'otp').decode()

        # Возвращаем результат верификации
        return client.post(
            otp_verify_url,
            {"phone": phone, "otp": correct_code},
            format='json'
        )
    return _flow


# =================================
# User fixtures
# =================================
@pytest.fixture
def user(db):
    """Тестовый пользователь."""
    return User.objects.create_user(
        phone='+79001234567',
        name='Pytester',
        email='test@tester.com'
    )


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


# =================================
# URL fixtures
# =================================
@pytest.fixture
def otp_send_url():
    return reverse('api:otp-send')


@pytest.fixture
def otp_verify_url():
    return reverse('api:otp-verify')
