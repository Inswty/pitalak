from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError


from products.models import IngredientInProduct


@pytest.mark.django_db
def test_unique_ingredient_in_product(product_auto, ingredient_honey):
    """Нельзя дважды добавить один и тот же ингредиент в один продукт."""

    IngredientInProduct.objects.create(
        product=product_auto,
        ingredient=ingredient_honey,
        amount_per_100g=Decimal('50.00')
    )

    # Ожидаем IntegrityError от UniqueConstraint в Meta
    with pytest.raises(IntegrityError):
        IngredientInProduct.objects.create(
            product=product_auto,
            ingredient=ingredient_honey,
            amount_per_100g=Decimal('10.00')
        )


@pytest.mark.django_db
def test_product_total_pfc_validation(product_manual):
    """Проверка: сумма БЖУ не может быть > 100г на 100г продукта."""

    # 40 + 40 + 30 = 110г (невозможно)
    product_manual.proteins = Decimal('40.0')
    product_manual.fats = Decimal('40.0')
    product_manual.carbs = Decimal('30.0')

    # Метод full_clean() должен выбросить ValidationError
    with pytest.raises(ValidationError) as exc:
        product_manual.full_clean()

    assert 'Сумма белков, жиров и углеводов не может быть больше 100 г' in (
        str(exc.value)
    )
