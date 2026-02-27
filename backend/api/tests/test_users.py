from rest_framework import status


def test_get_own_profile(auth_client, user, users_me_url):
    """Проверка получения данных своего профиля."""

    response = auth_client.get(users_me_url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['phone'] == str(user.phone)
    assert response.data['name'] == user.name
    assert set(['phone', 'name', 'email']).issubset(response.data.keys())


def test_update_profile_fields(auth_client, user, users_me_url):
    """Проверка обновления профиля."""

    new_name = 'Иван Иванович'
    new_email = 'vanyok@pitalak.ru'

    response = auth_client.patch(
        users_me_url, {
            "name": new_name,
            "email": new_email
        },
        format='json'
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.name == new_name
    assert user.email == new_email
    assert response.data['name'] == new_name
    assert response.data['email'] == new_email


def test_cannot_update_phone(auth_client, user, users_me_url):
    """Проверка - телефон нельзя сменить."""

    old_phone = str(user.phone)
    new_phone = '+79990000000'

    response = auth_client.patch(
        users_me_url, {"phone": new_phone}, format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    assert str(user.phone) == old_phone, 'Телефон нелья изменить'


def test_update_profile_invalid_email(auth_client, users_me_url):
    """Проверка валидации email."""

    response = auth_client.patch(
        users_me_url, {"email": "not-an-email"}, format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in response.data
