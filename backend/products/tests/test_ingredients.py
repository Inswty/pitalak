from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError


from products.models import Ingredient, NutrientInIngredient


@pytest.mark.django_db
def test_engredient_name_uniqueness():
    """Название ингредиента должно быть уникальным."""

    name = 'Макадамия'
    Ingredient.objects.create(name=name)

    with pytest.raises(ValidationError) as exc:
        Ingredient.objects.create(name=name)
    assert 'уже существует' in str(exc.value)


def test_ingredient_energy_value_calculation():
    """Проверка @property energy_value (формула 4/9/4)."""

    ingredient = Ingredient(
        name='Арахис',
        proteins=Decimal('26.0'),
        fats=Decimal('50.0'),
        carbs=Decimal('12.0')
    )

    # Energy: int(P*4 + F*9 + C*4)
    expected_energy = int(
        ingredient.proteins * Decimal('4')
        + ingredient.fats * Decimal('9')
        + ingredient.carbs * Decimal('4')
    )

    assert ingredient.energy_value == expected_energy


@pytest.mark.django_db
def test_ingredient_total_pfc_validation():
    """Проверка: сумма БЖУ не может быть > 100г на 100г продукта."""

    # 40 + 40 + 30 = 110г (невозможно)
    bad_ing = Ingredient(
        name='Ядерное топливо',
        proteins=Decimal('40.0'),
        fats=Decimal('40.0'),
        carbs=Decimal('30.0')
    )

    # Метод full_clean() должен выбросить ValidationError
    with pytest.raises(ValidationError) as exc:
        bad_ing.full_clean()

    assert 'Сумма белков, жиров и углеводов не может быть больше 100 г' in (
        str(exc.value)
    )


@pytest.mark.django_db
def test_unique_nutrient_in_ingredient(ingredient_honey, nutrient_vit_g):
    """Нельзя дважды добавить один и тот же нутриент в один ингредиент."""

    NutrientInIngredient.objects.create(
        ingredient=ingredient_honey,
        nutrient=nutrient_vit_g,
        amount_per_100g=Decimal('15.0')
    )

    with pytest.raises(IntegrityError):
        NutrientInIngredient.objects.create(
            ingredient=ingredient_honey,
            nutrient=nutrient_vit_g,
            amount_per_100g=Decimal('5.0')
        )
