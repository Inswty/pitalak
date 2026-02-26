from users.models import Address


def test_address_primary_auto_switching(user):
    """
    Проверка автоматического переключения основного
    адреса при создании и удалении.
    """

    # Первый адрес становится основным автоматом
    addr1 = Address.objects.create(user=user, street='Ленина', house='1')
    assert addr1.is_primary is True
    assert '[⭐]' in str(addr1)

    # Второй адрес НЕ основной по умолчанию
    addr2 = Address.objects.create(user=user, street='Мира', house='10')
    assert addr2.is_primary is False
    assert '[⭐]' not in str(addr2)

    # Делаем второй адрес основным — первый должен 'потухнуть'
    addr2.is_primary = True
    addr2.save()
    addr1.refresh_from_db()

    assert addr2.is_primary is True
    assert addr1.is_primary is False

    # Удаляем основной (addr2) — addr1 снова должен стать ⭐
    addr2.delete()
    addr1.refresh_from_db()
    assert addr1.is_primary is True
    assert '[⭐]' in str(addr1)


def test_single_address_always_stays_primary(user):
    """Проверка: если адрес единственный - он основной."""

    addr1 = Address.objects.create(user=user, street='Республики', house='10')
    assert addr1.is_primary is True
    addr1.is_primary = False
    addr1.save()
    addr1.refresh_from_db()
    assert addr1.is_primary is True, (
        'Единственный адрес потерял статус основного после сброса!'
    )
