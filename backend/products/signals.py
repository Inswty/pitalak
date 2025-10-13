import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product, Ingredient
from .services import ProductService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Product)
def update_product_after_saved(sender, instance, **kwargs):
    """После сохранения продукта — пересчитать PFC."""
    ProductService.recalc_and_save_pfc_safe(instance, reason='product saved')


@receiver(post_save, sender=Ingredient)
def update_all_product_with_change_ingredient(sender, instance, **kwargs):
    """При изменении ингредиента — обновить все связанные продукты."""
    ProductService.recalc_all_products_using_ingredient(instance)
