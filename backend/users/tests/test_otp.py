from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from users.otp_manager import OTPManager

User = get_user_model()


USER_PHONE = '+79001234567'


def test_sent_otp(client, redis_client, otp_send_url, mock_send_sms):
    """Проверка OTP: создание кода, сохранение в Redis и отправка SMS."""

    response = client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    assert response.status_code == status.HTTP_200_OK
    # В ответе есть 'detail', 'TTL' и только они
    assert set(response.data.keys()) == {'detail', 'TTL'}
    assert isinstance(response.data['TTL'], int)
    assert response.data['TTL'] > 0

    # Достаем ключи через менеджер
    keys = OTPManager._get_keys(USER_PHONE)
    # Проверяем, что OTP ключ существует в Redis
    assert redis_client.exists(keys['otp'])
    # Проверяем, что TTL для OTP установлен
    ttl = redis_client.ttl(keys['otp'])
    assert 0 < ttl <= response.data['TTL']
    # Проверяем наличие rate и cooldown ключей
    assert redis_client.exists(keys['rate'])
    assert redis_client.exists(keys['cooldown'])

    otp_data = redis_client.hgetall(keys['otp'])
    # Проверим, что хэш не пустой
    assert otp_data, f"Хэш {keys['otp']} пуст или не найден"
    otp_code = otp_data.get(b'otp').decode()

    assert len(otp_code) == 4
    assert otp_code.isdigit()

    # Проверяем, что SMS 'отправлен'
    mock_send_sms.assert_called_once()
    args, _ = mock_send_sms.call_args
    sent_otp = args[1]
    # Сравниваем с тем, что в Redis
    assert sent_otp == otp_code


def test_otp_cooldown_limit(client, otp_send_url, mock_send_sms):
    """Проверка ограничения по времени между двумя запросами (Cooldown)."""

    # Первый запрос — проходит успешно
    client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    # Второй запрос сразу же — должен вернуть 429
    response = client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert 'Подождите' in response.data['detail']


def test_otp_hourly_rate_limit(
        client, redis_client, otp_send_url, mock_send_sms
):
    """Проверка превышения лимита запроса OTP в час."""

    keys = OTPManager._get_keys(USER_PHONE)

    # Имитируем, израсходованный лимит
    redis_client.set(keys['rate'], settings.MAX_OTP_REQUESTS_PER_HOUR)

    # Делаем 'лишний' запрос
    response = client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert 'Превышен лимит запросов' in response.data['detail']


def test_otp_verification_attempts_limit(
        client, redis_client, otp_send_url, otp_verify_url, mock_send_sms
):
    """
    Тест на защиту от брутфорса:
    блокировка верификации и очистка кэша после исчерпания попыток.
    """

    # Создаем OTP
    client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    # Шлём неверный код до талого
    for i in range(settings.MAX_OTP_ATTEMPTS):
        response = client.post(
            otp_verify_url,
            {"phone": USER_PHONE, "otp": "0000"}, format='json'
        )
        if i < settings.MAX_OTP_ATTEMPTS - 1:
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert 'Неверный OTP' in response.data['detail']
        else:
            # Последняя попытка
            assert response.data['detail'] == 'Превышено количество попыток'

    # Ключ должен самоуничтожиться
    keys = OTPManager._get_keys(USER_PHONE)
    assert not redis_client.exists(keys['otp'])
