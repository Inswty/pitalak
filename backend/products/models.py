from django.db import models
from django.core.validators import MinValueValidator

from core.constants import (
    MAX_CHAR_LENGTH, MAX_INGREDIENT_LENGTH, MAX_PRICE_DIGITS, MAX_SLUG_LENGTH,
    MAX_STR_LENGTH, MAX_UNIT_LENGTH, PRICE_DECIMAL_PLACES
)


class Category(models.Model):
    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    slug = models.SlugField('Слаг', unique=True, max_length=MAX_SLUG_LENGTH)
    is_available = models.BooleanField(
        default=True, verbose_name='Доступен',
        help_text='Снимите галю, чтобы скрыть скрыть категорию.')

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'
        ordering = ('name',)

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Nutrient(models.Model):
    """Нутриент в составе ингредиента."""

    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_UNIT_LENGTH
    )
    rda = models.FloatField(
        'РСП', null=True, blank=True,
        help_text='Рекомендуемая суточная потребность'
    )

    class Meta:
        verbose_name = 'нутриент'
        verbose_name_plural = 'нутриенты'

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Ingredient(models.Model):
    """Ингредиент, входящий в состав продукта."""

    name = models.CharField('Название', max_length=MAX_INGREDIENT_LENGTH)
    proteins = models.FloatField('Белки', default=0,)
    fats = models.FloatField('Жиры', default=0)
    carbs = models.FloatField('Углеводы', default=0)
    nutrients = models.ManyToManyField(
        Nutrient,
        through='NutrientInIngredient',
        verbose_name='Нутриент',
        help_text='Выберите нутриенты и укажите их количество'
    )

    @property
    def energy_value(self):
        return int(self.proteins * 4 + self.fats * 9 + self.carbs * 4)

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'ингредиенты'

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Product(models.Model):
    """Продукт с фото и описанием."""

    class NutritionMode(models.TextChoices):
        NONE = 'none', 'Без БЖУ'
        AUTO = 'auto', 'Рассчитать из ингредиентов'
        MANUAL = 'manual', 'Ввести вручную'

    name = models.CharField('Название', max_length=MAX_CHAR_LENGTH)
    nutrition_mode = models.CharField(
        max_length=10,
        choices=NutritionMode.choices,
        default=NutritionMode.NONE,
    )
    proteins = models.FloatField('Белки', default=0,)
    fats = models.FloatField('Жиры', default=0)
    carbs = models.FloatField('Углеводы', default=0)
    energy_value = models.PositiveIntegerField(
        'Энергетическая ценность',
        help_text='Энергетическая ценность продукта, ккал',
    )
    description = models.TextField('Описание', blank=True, null=True)
    image = models.ImageField(
        'Фото', upload_to='images', blank=True, null=True
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInProduct',
        verbose_name='Ингредиенты',
        help_text='Выберите ингредиенты и укажите их количество'
    )
    weight = models.FloatField(
        help_text='Вес (гр.)',
        blank=True, null=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )
    is_available = models.BooleanField(
        default=True, verbose_name='Доступен',
        help_text='Снимите галю, чтобы скрыть товар.')
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
