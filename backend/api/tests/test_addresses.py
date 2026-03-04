from django.contrib.auth import get_user_model
from rest_framework import status

from users.models import Address

User = get_user_model()


def test_user_cannot_see_other_user_addresses(auth_client, address_url):
    """Проверка фильтрации: в списке только свои адреса."""

    other_user = User.objects.create_user(phone='+79009998877')
    Address.objects.create(user=other_user, street='Чужая', house='666')

    # Получаем список адресов
    response = auth_client.get(address_url)
    assert response.status_code == status.HTTP_200_OK
    # Ожидаем пустой список
    assert response.data['count'] == 0


def test_user_cannot_delete_other_user_address(auth_client, address_url):
    """Проверка безопасности: нельзя удалить чужой адрес по ID."""

    other_user = User.objects.create_user(phone='+79009998877')
    other_addr = Address.objects.create(user=other_user,
                                        street='Чужая', house='666')
    # Пытаемся удалить чужой адрес
    delete_url = f'{address_url}{other_addr.id}/'
    response = auth_client.delete(delete_url)
    # Ожидаем 404
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Address.objects.filter(id=other_addr.id).exists()


def test_user_cannot_update_other_user_address(auth_client, address_url):
    """Проверка защиты от IDOR: нельзя изменить чужой адрес через PATCH."""

    other_user = User.objects.create_user(phone='+79001112233')
    other_addr = Address.objects.create(
        user=other_user, street='Чужая', house='666'
    )

    patch_url = f'{address_url}{other_addr.id}/'

    response = auth_client.patch(
        patch_url,
        {'street': 'Взломанная'},
        format='json'
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    other_addr.refresh_from_db()
    assert other_addr.street == 'Чужая'


def test_user_can_create_address(auth_client, user, address_url):
    """Проверка создания адреса и его автоматической пометки как основной."""

    data = {"street": "Тестовая", "house": "1"}
    response = auth_client.post(address_url, data, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    address = Address.objects.filter(user=user).last()
    # Сравниваем поля в базе с отправленными данными
    assert address.street == data['street']
    assert address.house == data['house']
    assert address.is_primary is True
    # Сравниваем данные в ответе API с данными в базе
    assert response.data['street'] == address.street
    assert response.data['house'] == address.house
    assert response.data['is_primary'] is True


def test_user_can_retrieve_own_address(auth_client, user_address, address_url):
    """Проверка получения деталей адреса и соответствия структуры полей."""

    url = f'{address_url}{user_address.id}/'

    response = auth_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    expected_fields = {
        'id', 'locality', 'street', 'house', 'flat', 'floor', 'is_primary'
    }
    assert expected_fields.issubset(response.data.keys())
    assert response.data['id'] == user_address.id
    assert response.data['street'] == user_address.street
    assert response.data['is_primary'] == user_address.is_primary


def test_address_update_own(auth_client, user_address, address_url):
    """Проверка, что юзер может изменить свой адрес."""

    url = f'{address_url}{user_address.id}/'
    new_street = 'Новая Улица'

    response = auth_client.patch(url, {"street": new_street}, format='json')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['street'] == new_street
    assert response.data['is_primary'] is True


def test_address_delete_primary_logic_api(
    auth_client, user, user_address, address_url
):
    """
    При удалении основного адреса через API,
    последний должен стать основным.
    """

    # Создаем второй адрес
    second_addr = Address.objects.create(user=user, street='Вторая', house='2')
    third_addr = Address.objects.create(user=user, street='Третья', house='3')

    assert second_addr.is_primary is False

    # Удаляем первый через ручку
    url = f'{address_url}{user_address.id}/'
    response = auth_client.delete(url)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Address.objects.filter(id=user_address.id).exists()

    # Третий адрес должен стать основным
    third_addr.refresh_from_db()
    assert third_addr.is_primary is True
    assert Address.objects.filter(user=user, is_primary=True).count() == 1
