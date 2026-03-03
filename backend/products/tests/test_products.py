from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError


from products.models import Ingredient, IngredientInProduct, Product


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


def test_product_recalc_auto_mode(product_auto):
    """Проверка автоматического пересчета БЖУ в Product (AUTO)."""

    ingredients_data = [
        {'name': 'Орешка', 'p': 10.0, 'f': 5.0, 'c': 30.0, 'amount': 30.0},
        {'name': 'Мёдушка', 'p': 5.0, 'f': 3.5, 'c': 70.0, 'amount': 20.0},
    ]

    for data in ingredients_data:
        ing = Ingredient.objects.create(
            name=data['name'],
            proteins=Decimal(str(data['p'])),
            fats=Decimal(str(data['f'])),
            carbs=Decimal(str(data['c']))
        )
        IngredientInProduct.objects.create(
            product=product_auto,
            ingredient=ing,
            amount_per_100g=Decimal(str(data['amount']))
        )

    product_auto.recalc_nutrition()

    # Формула: Сумма (БЖУ * (Кол-во / 100))
    totals = {key: Decimal('0') for key in ['p', 'f', 'c']}
    for d in ingredients_data:
        ratio = Decimal(str(d['amount'])) / Decimal('100')
        for key in totals:
            totals[key] += Decimal(str(d[key])) * ratio

    assert product_auto.nutrition_mode == product_auto.NutritionMode.AUTO

    # Energy: int(P*4 + F*9 + C*4)
    total_energy = int(totals['p'] * 4 + totals['f'] * 9 + totals['c'] * 4)

    assert product_auto.proteins == totals['p'].quantize(Decimal('0.1'))
    assert product_auto.fats == totals['f'].quantize(Decimal('0.1'))
    assert product_auto.carbs == totals['c'].quantize(Decimal('0.1'))
    assert product_auto.energy_value == total_energy


def test_product_post_save_signal_triggers_recalc(
    product_auto, ingredient_honey, force_on_commit_execution
):
    """Проверка: post_save(Product) запускает пересчет питания."""

    # Energy: int(P*4 + F*9 + C*4)
    expected_energy = int(
        ingredient_honey.proteins * Decimal(4)
        + ingredient_honey.fats * Decimal(9)
        + ingredient_honey.carbs * Decimal(4)
    )

    assert product_auto.energy_value == 0

    IngredientInProduct.objects.create(
        product=product_auto,
        ingredient=ingredient_honey,
        amount_per_100g=Decimal('100.00')
    )
    product_auto.save()
    product_auto.refresh_from_db()

    # Проверяем, что сигнал изменил energy_value
    assert product_auto.energy_value == expected_energy
    # 100% ингредиента → значения должны совпасть
    assert product_auto.proteins == ingredient_honey.proteins
    assert product_auto.fats == ingredient_honey.fats
    assert product_auto.carbs == ingredient_honey.carbs


def test_recalc_all_products_via_service(product_auto, ingredient_honey):
    """Проверка: изменение ингредиента обновляет ВСЕ связанные продукты."""

    # Создаем второй продукт
    product_auto_2 = Product.objects.create(
        name='Конфета 2',
        nutrition_mode=Product.NutritionMode.AUTO,
        category=product_auto.category,
        price=Decimal('150.00')
    )

    # Привязываем мёд к обоим продуктам (по 100г)
    for p in (product_auto, product_auto_2):
        IngredientInProduct.objects.create(
            product=p, ingredient=ingredient_honey,
            amount_per_100g=Decimal('100')
        )

    # Меняем белки в мёде (было 0.5, стало 2)
    ingredient_honey.proteins = Decimal('2.0')
    ingredient_honey.save()
    # Energy: int(P*4 + F*9 + C*4)
    expected_energy = int(
        ingredient_honey.proteins * Decimal('4')
        + ingredient_honey.fats * Decimal('9')
        + ingredient_honey.carbs * Decimal('4')
    )

    product_auto.refresh_from_db()
    product_auto_2.refresh_from_db()

    assert product_auto.proteins == Decimal('2.0')
    assert product_auto_2.proteins == Decimal('2.0')
    assert product_auto.energy_value == expected_energy
    assert product_auto_2.energy_value == expected_energy


def test_product_recalc_skipped_in_manual_mode(
    product_manual, ingredient_honey, force_on_commit_execution
):
    """Проверка: в режиме MANUAL автоматика не перезаписывает ручные данные."""

    initial_pfc = {
        'p': product_manual.proteins,
        'f': product_manual.fats,
        'c': product_manual.carbs
    }

    # Energy: int(P*4 + F*9 + C*4)
    expected_energy = int(
        product_manual.proteins * Decimal('4')
        + product_manual.fats * Decimal('9')
        + product_manual.carbs * Decimal('4')
    )

    # Добавляем ингредиент, который при AUTO изменил бы PFC
    IngredientInProduct.objects.create(
        product=product_manual,
        ingredient=ingredient_honey,
        amount_per_100g=Decimal('100.00')
    )
    product_manual.save()
    product_manual.refresh_from_db()

    current_pfc = {
        'p': product_manual.proteins,
        'f': product_manual.fats,
        'c': product_manual.carbs
    }

    assert product_manual.nutrition_mode == Product.NutritionMode.MANUAL
    # PFC не должны измениться
    assert current_pfc == initial_pfc
    # Energy_value должен быть корректно посчитан
    assert product_manual.energy_value == expected_energy


def test_product_recalc_to_zero_when_no_ingredients(
    product_auto, ingredient_honey, force_on_commit_execution
):
    """Проверка: если удалить все ингредиенты, БЖУ продукта обнуляются."""

    link = IngredientInProduct.objects.create(
        product=product_auto, ingredient=ingredient_honey, amount_per_100g=100
    )
    product_auto.save()

    # Удаляем связь (ингредиент)
    link.delete()

    product_auto.save()
    product_auto.refresh_from_db()

    assert product_auto.proteins == 0
    assert product_auto.energy_value == 0


def test_product_recalc_skipped_in_none_mode(
    product_auto, ingredient_honey, force_on_commit_execution
):
    """Проверка: в режиме NONE БЖУ = 0, даже если есть ингредиенты."""

    product_auto.nutrition_mode = Product.NutritionMode.NONE

    IngredientInProduct.objects.create(
        product=product_auto, ingredient=ingredient_honey, amount_per_100g=100
    )
    product_auto.save()
    product_auto.refresh_from_db()

    assert product_auto.proteins == 0
    assert product_auto.energy_value == 0
