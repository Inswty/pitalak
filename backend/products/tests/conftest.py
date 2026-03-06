from decimal import Decimal

import pytest

from products.models import Ingredient, Nutrient


@pytest.fixture()
def force_on_commit_execution(monkeypatch):
    """
    Принудительно выполняет callback-функции transaction.on_commit немедленно.

    В pytest тесты по умолчанию оборачиваются в транзакцию, которая никогда
    не фиксируется (rollback), из-за чего обработчики on_commit не запускаются.
    Фикстура подменяет механизм коммита для тестирования логики ProductService.
    """
    def immediate(func):
        return func()
    monkeypatch.setattr('products.services.transaction.on_commit', immediate)


@pytest.fixture
def ingredient_honey(db):
    return Ingredient.objects.create(
        name='Мёд',
        proteins=Decimal('0.5'),
        fats=Decimal('0.0'),
        carbs=Decimal('80.0')
    )


@pytest.fixture
def nutrient_vit_g():
    return Nutrient.objects.create(
        name='Витамин Ж',
        measurement_unit='мкг',
        rda=Decimal(0.012)
    )
