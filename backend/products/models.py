from django.db import models
from django.core.validators import MinValueValidator

from core.constants import (
    MAX_CHAR_LENGTH, MAX_INGREDIENT_LENGTH, MAX_PRICE_DIGITS, MAX_STR_LENGTH,
    MAX_UNIT_LENGTH, PRICE_DECIMAL_PLACES
)


class Nutrient(models.Model):
    """Нутриент в составе ингредиента."""

    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_UNIT_LENGTH
    )

    class Meta:
        verbose_name = 'нутриент'
        verbose_name_plural = 'нутриенты'

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Ingredient(models.Model):
    """Ингредиент, входящий в состав продукта."""

    name = models.CharField('Название', max_length=MAX_INGREDIENT_LENGTH)
    nutrients = models.ManyToManyField(
        Nutrient,
        through='NutrientInIngredient',
        verbose_name='Ингредиенты',
        help_text='Выберите нутриенты и укажите их количество'
    )
    energy_value = models.PositiveIntegerField(
        help_text='Энергетическая ценность на 100 г, ккал',
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'ингредиенты'

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Product(models.Model):
    """Продукт с фото и описанием."""

    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    description = models.TextField('Описание', blank=True, null=True)
    image = models.ImageField('Фото', upload_to='images')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInProduct',
        verbose_name='Ингредиенты',
        help_text='Выберите ингредиенты и укажите их количество'
    )
    energy_value = models.PositiveIntegerField(
        help_text='Энергетическая ценность продукта, ккал',
    )
    price = models.DecimalField(
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        default=0.00,
        help_text='Цена'
    )

    class Meta:
        verbose_name = 'продукт'
        verbose_name_plural = 'продукты'

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class IngredientInProduct(models.Model):
    """Промежуточная модель для количества ингредиента в продукте."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_ingredients',
        verbose_name='Продукт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='product_links',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=(MinValueValidator(1),),
        help_text='Укажите количество этого ингредиента в гр.'
    )

    class Meta:
        verbose_name = 'ингредиент в продукте'
        verbose_name_plural = 'ингредиенты в продуктах'
        constraints = (
            models.UniqueConstraint(
                fields=('product', 'ingredient'),
                name='unique_ingredient_in_product'
            ),
        )

    def __str__(self):
        return f'{self.ingredient} — {self.amount} ({self.product})'


class NutrientInIngredient(models.Model):
    """Промежуточная модель количества нутриента в ингредиенте на 100 г."""

    nutrient = models.ForeignKey(
        Nutrient,
        on_delete=models.CASCADE,
        related_name='nutrient_ingredients',
        verbose_name='Нутриент'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='nutrient_links',
        verbose_name='Ингредиент'
    )
    amount_per_100g = models.PositiveIntegerField(
        verbose_name='Количество',
        validators=(MinValueValidator(1),),
        help_text='Количество нутриента на 100 г ингредиента'
    )

    class Meta:
        verbose_name = 'нутриент в ингредиенте'
        verbose_name_plural = 'нутриенты в ингредиентах'
        constraints = (
            models.UniqueConstraint(
                fields=('nutrient', 'ingredient'),
                name='unique_ingredient_in_nutrient'
            ),
        )

    def __str__(self):
        return f'{self.ingredient} — {self.amount_per_100g} ({self.nutrient})'
