import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from orders.models import CartItem


def test_unique_product_in_cart(cart, product_auto):
    """Нельзя добавить один и тот же товар в корзину дважды."""

    CartItem.objects.create(cart=cart, product=product_auto)
    with pytest.raises(IntegrityError):
        CartItem.objects.create(cart=cart, product=product_auto)


def test_cart_item_quantity_must_be_positive(cart, product_auto):
    """Количество товара должно быть >= 1."""

    valid_item = CartItem(cart=cart, product=product_auto, quantity=1)
    valid_item.full_clean()  # Не бросает исключение

    invalid_item = CartItem(cart=cart, product=product_auto, quantity=0)
    with pytest.raises(ValidationError):
        invalid_item.full_clean()
