import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from users.otp_manager import OTPManager

User = get_user_model()


USER_PHONE = '+79001234567'


def test_send_otp_api_response(client, otp_send_url, mock_send_sms):
    """Проверка структуры ответа API."""

    response = client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    assert response.status_code == status.HTTP_200_OK
    # В ответе есть 'detail', 'TTL' и только они
    assert set(response.data.keys()) == {'detail', 'TTL'}
    assert isinstance(response.data['TTL'], int)
    assert response.data['TTL'] > 0


def test_send_otp_redis_storage(
    client, redis_client, otp_send_url, mock_send_sms
):
    """Проверка корректного сохранения данных в Redis."""

    response = client.post(otp_send_url, {"phone": USER_PHONE}, format='json')
    keys = OTPManager._get_keys(USER_PHONE)

    # Проверка существования и TTL
    assert redis_client.exists(keys['otp'])
    assert redis_client.exists(keys['rate'])
    assert redis_client.exists(keys['cooldown'])
    ttl = redis_client.ttl(keys['otp'])
    assert 0 < ttl <= response.data['TTL']

    # Проверка otp-кода
    otp_data = redis_client.hgetall(keys['otp'])
    assert otp_data, f"Хэш {keys['otp']} пуст"
    otp_code = otp_data.get(b'otp').decode()
    assert len(otp_code) == 4
    assert otp_code.isdigit()


def test_send_otp_sms_delivery(
    client, redis_client, otp_send_url, mock_send_sms
):
    """Проверка, что SMS отправляется с верным кодом."""

    client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    keys = OTPManager._get_keys(USER_PHONE)
    otp_code = redis_client.hget(keys['otp'], b'otp').decode()

    mock_send_sms.assert_called_once()
    # Проверка на соответствие кода в SMS и Redis
    args, _ = mock_send_sms.call_args
    assert args[1] == otp_code


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


@pytest.mark.django_db
def test_otp_verification_success(
    client, otp_send_url, otp_verify_url, redis_client, mock_send_sms
):
    """Проверка успешной верификации: вход по верному коду и очистка Redis."""

    # Создаем OTP
    client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    # Достаем реальный код из Redis
    keys = OTPManager._get_keys(USER_PHONE)
    otp_data = redis_client.hgetall(keys['otp'])
    correct_code = otp_data.get(b'otp').decode()

    # Вводим правильный код
    response = client.post(
        otp_verify_url,
        {"phone": USER_PHONE, "otp": correct_code},
        format='json'
    )

    assert response.status_code == status.HTTP_200_OK
    # В ответе есть только 'access', 'refresh'
    assert set(response.data.keys()) == {'access', 'refresh'}
    # OTP должен быть удален из Redis
    assert not redis_client.exists(keys['otp'])
    # SMS 'отправлен' один раз
    mock_send_sms.assert_called_once()


@pytest.mark.parametrize('dirty_phone, expected_clean', (
    ('89001234567', '+79001234567'),
    ('+7 900 123 45 67', '+79001234567'),
    ('79001234567', '+79001234567'),
    (' +7(900)123-45-67 ', '+79001234567'),
))
def test_otp_phone_normalization(
    client, redis_client, otp_send_url, dirty_phone, expected_clean,
    mock_send_sms
):
    """Проверка - любые форматы номера превращаются в единый ключ в Redis."""

    # Отправляем 'грязный' номер
    client.post(otp_send_url, {"phone": dirty_phone}, format='json')

    # Генерим эталонный ключ через менеджер
    expected_keys = OTPManager._get_keys(expected_clean)

    assert redis_client.exists(expected_keys['otp']), \
        f'Номер {dirty_phone} не был приведен к {expected_clean}'


@pytest.mark.parametrize('invalid_phone', (
    'абракадабра',         # Просто текст
    '123',                 # Слишком короткий
    '89001234567890123',   # Слишком длинный
    '',                    # Слишком пустой
    '+7 (000) 000-00-00',  # Несуществующий код/номер
    'None',                # 'None'
))
def test_sent_otp_invalid_phone(
    client, otp_send_url, invalid_phone, mock_send_sms
):
    """Проверка - ручка OTP не пропускает невалидные номера телефонов."""

    response = client.post(
        otp_send_url, {"phone": invalid_phone}, format='json'
    )

    # Ожидаем 400 Bad Request
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # В ответе инфа об ошибке в поле phone
    assert 'phone' in response.data


@pytest.mark.django_db
def test_otp_expired_code(
    client, redis_client, otp_verify_url, otp_send_url, mock_send_sms
):
    """Проверка, что просроченный код не проходит верификацию."""

    client.post(otp_send_url, {"phone": USER_PHONE}, format='json')

    keys = OTPManager._get_keys(USER_PHONE)
    otp_data = redis_client.hgetall(keys['otp'])
    correct_code = otp_data.get(b'otp').decode()

    redis_client.expire(keys['otp'], 0)  # Принудительно 'протухаем' ключ

    # Пытаемся верифицироваться
    response = client.post(
        otp_verify_url,
        {"phone": USER_PHONE, "otp": correct_code}, format='json'
    )
    assert not redis_client.exists(keys['otp'])
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'истек' in response.data['detail']
    assert 'access' not in response.data


@pytest.mark.django_db
def test_otp_verification_creates_new_user(auth_otp_flow):
    """Проверка создания пользователя после успешной верификации."""

    # Убеждаемся, что юзера с таким номером НЕТ в базе
    assert not User.objects.filter(phone=USER_PHONE).exists()

    response = auth_otp_flow(USER_PHONE)
    assert response.status_code == status.HTTP_200_OK

    # Юзер должен появиться в БД
    assert User.objects.filter(phone=USER_PHONE).exists()
    assert set(response.data.keys()) == {'access', 'refresh'}


@pytest.mark.django_db
def test_otp_verification_existing_user(auth_otp_flow):
    """
    Проверка, что для существующего юзера
    не создается дубликат и выдаются токены.
    """

    # Заранее создаем юзера в базе
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.create_user(phone=USER_PHONE)
    initial_count = User.objects.count()

    response = auth_otp_flow(USER_PHONE)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data.keys()) == {'access', 'refresh'}

    # Количество юзеров не изменилось
    assert User.objects.count() == initial_count


@pytest.mark.django_db
def test_user_verified_after_correct_otp(auth_otp_flow):
    """Проверка: после ввода верного OTP: phone_verified == True."""

    response = auth_otp_flow(USER_PHONE)
    assert response.status_code == status.HTTP_200_OK

    user = User.objects.get(phone=USER_PHONE)
    assert user.phone_verified is True
