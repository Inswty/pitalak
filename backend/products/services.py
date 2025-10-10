from django.db import transaction


class ProductService:
    @staticmethod
    @transaction.atomic
    def recalc_product(instance):
        data = instance.recalc_nutrition()

        # определяем какие поля обновить
        fields = ['energy_value']
        if instance.nutrition_mode == instance.NutritionMode.AUTO:
            fields += ['proteins', 'fats', 'carbs']

        # формируем словарь только нужных полей
        update_data = {field: data[field] for field in fields}

        # обновляем напрямую в базе (без сигналов)
        instance.__class__.objects.filter(pk=instance.pk).update(**update_data)

        # синхронизируем объект в памяти
        for field, value in update_data.items():
            setattr(instance, field, value)
