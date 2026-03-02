from decimal import Decimal

import pytest

from products.models import Ingredient, Nutrient, Product


@pytest.fixture
def product_auto(category):
    """Заготовка продукта в режиме AUTO."""
    return Product.objects.create(
        name='Конфета AUTO',
        category=category,
        nutrition_mode=Product.NutritionMode.AUTO,
        price=Decimal('100.00')
    )


@pytest.fixture
def product_manual(category):
    """Заготовка продукта в режиме MANUAL."""
    return Product.objects.create(
        name='Конфета MANUAL',
        category=category,
        nutrition_mode=Product.NutritionMode.MANUAL,
        price=Decimal('100.00'),
        proteins=Decimal('5.0'),
        fats=Decimal('1.0'),
        carbs=Decimal('80.0')
    )


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
