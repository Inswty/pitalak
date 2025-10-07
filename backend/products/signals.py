import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import IngredientInProduct, Product, Ingredient

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=IngredientInProduct)
def update_product_nutrition(sender, instance, **kwargs):
    """
    Обновляет nutrition продукта при изменении состава ингредиентов.
    """
    product = instance.product
    # Проверяем, что продукт уже сохранен в БД
    if product.pk is None:
        logger.warning(
            'Пропуск пересчёта nutrition: продукт ещё не сохранён.'
            ' IngredientInProduct id=%s',
            instance.product,
        )
        return
    elif product.nutrition_mode != Product.NutritionMode.AUTO:
        logger.info('Состав ингредиентов продукта "%s" был изменен, пропуск '
                    'пересчета nutritions: ручной режим рассчетов.',
                    instance.product)
        return
    logger.info('Состав ингредиентов продукта "%s" был изменен, запущен'
                ' пересчет nutritions', instance.product)
    product.recalc_nutrition(save=True)


@receiver(post_save, sender=Ingredient)
def update_products_on_ingredient_change(sender, instance, **kwargs):
    """
    Обновляет все продукты, использующие этот ингредиент, при его изменении.
    """
    # Используем select_related для оптимизации запросов
    for link in instance.product_links.select_related('product').all():
        product = link.product
        if product.pk is None:
            logger.warning(
                'Пропуск пересчёта nutrition: ингредиент ещё не сохранён.'
                ' Ingredient id=%s',
                instance.name,
            )
            continue
        elif product.nutrition_mode != Product.NutritionMode.AUTO:
            logger.info('Продукт %s, пропуск пересчета nutritions: '
                        'ручной режим рассчетов.', product.name)
            continue
        logger.info('Состав ингредиента "%s" был изменен, запущен'
                    ' пересчет nutritions %s', instance.name, product.name)
        product.recalc_nutrition(save=True)
