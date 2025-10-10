import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.core.validators import MinValueValidator

from core.constants import (
    MAX_CHAR_LENGTH, MAX_INGREDIENT_LENGTH, MAX_PRICE_DIGITS, MAX_SLUG_LENGTH,
    MAX_STR_LENGTH, MAX_UNIT_LENGTH, PRICE_DECIMAL_PLACES
)

logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField(
        'Название', unique=True, max_length=MAX_CHAR_LENGTH
    )
    slug = models.SlugField('Слаг', unique=True, max_length=MAX_SLUG_LENGTH)
    is_available = models.BooleanField(
        default=True, verbose_name='Доступен',
        help_text='Снимите галю, чтобы скрыть категорию.')

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'Категории'
        ordering = ('name',)

    def __str__(self):
        return self.name[:MAX_STR_LENGTH]


class Nutrient(models.Model):
    """Нутриент в составе ингредиента."""

    name = models.CharField(
        'Название', unique=True, max_length=MAX_CHAR_LENGTH
    )
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

    name = models.CharField(
        'Название', unique=True, max_length=MAX_INGREDIENT_LENGTH
    )
    proteins = models.DecimalField(
        'Белки', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
    fats = models.DecimalField(
        'Жиры', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
    carbs = models.DecimalField(
        'Углеводы', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
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
        'БЖУ',
        max_length=10,
        choices=NutritionMode.choices,
        default=NutritionMode.NONE,
    )
    proteins = models.DecimalField(
        'Белки', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
    fats = models.DecimalField(
        'Жиры', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
    carbs = models.DecimalField(
        'Углеводы', max_digits=5, decimal_places=1, default=Decimal('0.0'),
        validators=[MinValueValidator(0)]
    )
    energy_value = models.PositiveIntegerField(
        'Энергетическая ценность, ккал',
        help_text='Энергетическая ценность продукта, ккал',
        blank=True, null=True,
        default=0
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
        'Вес',
        help_text='Вес (гр.)',
        blank=True, null=True, default=0
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )
    is_available = models.BooleanField(
        'Доступен', default=True,
        help_text='Снимите галю, чтобы скрыть товар.')
    price = models.DecimalField(
        'Цена',
        max_digits=MAX_PRICE_DIGITS,
        decimal_places=PRICE_DECIMAL_PLACES,
        validators=[MinValueValidator(0.009)],
        default=0.00,
        help_text='Цена, руб.'
    )

    def recalc_nutrition(self, save: bool = True):
        """Пересчёт БЖУ и калорийности из ингредиентов."""
        try:
            # Транзакция для защиты при одновременных изменениях состава
            with transaction.atomic():
                if self.nutrition_mode == self.NutritionMode.AUTO:
                    # Инициализируем переменные для БЖУ
                    proteins = fats = carbs = Decimal('0')
                    for link in self.product_ingredients.select_related(
                        'ingredient'
                    ):
                        ingredient = link.ingredient
                        ratio = Decimal(link.amount) / Decimal('100')
                        proteins += ingredient.proteins * ratio
                        fats += ingredient.fats * ratio
                        carbs += ingredient.carbs * ratio
                    # Округляем до 2 знаков после запятой
                    self.proteins = proteins.quantize(Decimal('0.01'),
                                                      rounding=ROUND_HALF_UP)
                    self.fats = fats.quantize(Decimal('0.01'),
                                              rounding=ROUND_HALF_UP)
                    self.carbs = carbs.quantize(Decimal('0.01'),
                                                rounding=ROUND_HALF_UP)
                # Калорийность
                self.energy_value = int(
                    self.proteins * Decimal('4')
                    + self.fats * Decimal('9')
                    + self.carbs * Decimal('4')
                )
                logger.info('Успешный пересчёт nutrition для продукта'
                            ' "%s"', self.name)
                return {
                    'proteins': proteins,
                    'fats': fats,
                    'carbs': carbs,
                    'energy_value': self.energy_value
                }

        except Exception:
            logger.exception(
                'Ошибка при пересчёте nutrition для Product "%s"',
                self.name,
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
    amount = models.DecimalField(
        verbose_name='Количество на 100 г.',
        max_digits=6,
        decimal_places=1,  # Одна цифра после запятой
        validators=(MinValueValidator(0.1),),
        help_text='Укажите количество этого ингредиента в граммах'
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
    amount_per_100g = models.DecimalField(
        verbose_name='Количество',
        max_digits=6,
        decimal_places=1,  # Одна цифра после запятой
        validators=(MinValueValidator(0.1),),
        help_text='Количество нутриента на 100 г ингредиента (в граммах)'
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
