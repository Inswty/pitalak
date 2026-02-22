import pytest
from django.urls import reverse

from core.redis_client import RedisClient


@pytest.fixture
def mock_send_sms(mocker):
    """Мок для асинхронной отправки OTP через Celery."""
    return mocker.patch('users.tasks.send_otp_sms_task.delay')


@pytest.fixture
def redis_client():
    """Фикстура Redis с очисткой до и после теста."""
    with RedisClient.connect() as client:
        # Очищаем Redis перед тестом
        client.flushdb()
        yield client
        # Очищаем Redis после теста
        client.flushdb()


# =================================
# URL fixtures
# =================================
@pytest.fixture
def otp_send_url():
    return reverse('api:otp-send')


@pytest.fixture
def otp_verify_url():
    return reverse('api:otp-verify')
