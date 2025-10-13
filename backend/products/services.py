from django.db import transaction
import logging

from .models import Product

logger = logging.getLogger(__name__)


class ProductService:

    UPDATE_FIELDS = ['proteins', 'fats', 'carbs', 'energy_value']

    @staticmethod
    def _should_skip_recalc(product, reason=None):
        if not product or not getattr(product, 'pk', None):
            logger.warning(
                'Пропуск пересчёта: продукт не сохранён. reason=%s', reason
            )
            return True
        if product.nutrition_mode == Product.NutritionMode.NONE:
            logger.info(
                'Пропуск пересчёта "%s": режим "%s". reason=%s',
                product.name,
                product.get_nutrition_mode_display(),
                reason,
            )
            return True
        return False

    @staticmethod
    def recalc_and_save_pfc_safe(product, reason=None):
        """Безопасный пересчёт PFC продукта."""
        if ProductService._should_skip_recalc(product, reason):
            return
        logger.info(
            'Пересчёт PFC "%s" инициирован (reason=%s)',
            product.name,
            reason,
        )
        transaction.on_commit(
            lambda: ProductService._recalc_and_save_pfc(product)
        )

    @staticmethod
    @transaction.atomic
    def _recalc_and_save_pfc(product):
        """Пересчёт и обновление полей."""
        data = product.recalc_nutrition()

        fields = ['energy_value']
        if product.nutrition_mode == product.NutritionMode.AUTO:
            fields += ['proteins', 'fats', 'carbs']

        update_data = {field: data[field] for field in fields}
        product.__class__.objects.filter(pk=product.pk).update(**update_data)

        # синхронизируем объект в памяти
        for field, value in update_data.items():
            setattr(product, field, value)

        logger.info('Пересчёт PFC для "%s" успешно завершён', product.name)

    @staticmethod
    def recalc_all_products_using_ingredient(ingredient):
        """
        Пересчитывает PFC для всех продуктов, использующих данный ингредиент.
        """
        # Находим все продукты, где используется этот ингредиент
        products = (
            Product.objects.filter(product_ingredients__ingredient=ingredient)
            .distinct()
        )
        if not products.exists():
            logger.info(
                'Нет продуктов, использующих ингредиент "%s" '
                '— пересчёт не требуется.',
                ingredient.name,
            )
            return
        updated_products = []
        for product in products:
            # Пропускаем несохранённые и ручные режимы
            if ProductService._should_skip_recalc(
                product, reason=f'ingredient "{ingredient.name}" changed'
            ):
                continue
            # Пересчёт нутриентов
            data = product.recalc_nutrition()
            for field in ProductService.UPDATE_FIELDS:
                setattr(product, field, data[field])
            updated_products.append(product)
        # Массовое обновление
        if updated_products:
            with transaction.atomic():
                Product.objects.bulk_update(
                    updated_products,
                    ProductService.UPDATE_FIELDS,
                    batch_size=100,
                )
            logger.info(
                'Обновлено %d продуктов, содержащих ингредиент "%s".',
                len(updated_products),
                ingredient.name,
            )
