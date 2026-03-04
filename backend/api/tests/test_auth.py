import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

USER_PHONE = '+79001234567'


@pytest.mark.django_db
def test_token_refresh_flow(client, auth_otp_flow, token_refresh_url):
    """Проверка: эндпойнт возвращает refresh токен."""

    response = auth_otp_flow(USER_PHONE)
    refresh_token = response.data['refresh']

    # Стучимся в эндпоинт обновления
    refresh_response = client.post(
        token_refresh_url, {'refresh': refresh_token},
        format='json'
    )

    # Проверяем, что там новый access, refresh
    assert refresh_response.status_code == status.HTTP_200_OK
    assert {'access', 'refresh'}.issubset(refresh_response.data)
    assert refresh_response.data['refresh'] != refresh_token


@pytest.mark.django_db
def test_refresh_fails_for_inactive_user(
    client, auth_otp_flow, token_refresh_url, users_me_url
):
    """Проверка: заблокированный пользователь не может обновить токен."""

    # Получаем токены
    response = auth_otp_flow(USER_PHONE)
    refresh_token = response.data['refresh']

    # Находим и блокируем
    user = User.objects.get(phone=USER_PHONE)
    user.is_active = False
    user.save()

    # Проверим, что пользователь уже заблокирован
    response = client.get(users_me_url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Пытаемся обновиться по старому refresh
    refresh_response = client.post(
        token_refresh_url,
        {'refresh': refresh_token},
        format='json'
    )

    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert refresh_response.data['detail'].code == 'no_active_account'
