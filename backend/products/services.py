from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class ProductService:
    @staticmethod
    def recalc_and_save_pfc_safe(product, reason=None):
        """Безопасный пересчёт PFC продукта."""
        if not product or not getattr(product, 'pk', None):
            logger.warning(
                'Пропуск пересчёта PFC: продукт не сохранён. reason=%s', reason
            )
            return
        if product.nutrition_mode == product.NutritionMode.NONE:
            logger.info(
                'Пропуск пересчёта PFC "%s": ручной режим. reason=%s',
                product.name,
                reason,
            )
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
        """Непосредственно пересчёт и обновление полей."""
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
