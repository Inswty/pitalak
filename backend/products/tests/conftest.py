from decimal import Decimal

import pytest

from products.models import Ingredient, Nutrient


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
