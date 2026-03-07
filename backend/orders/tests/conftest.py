import pytest

from orders.models import ShoppingCart


@pytest.fixture
def cart(user):
    return ShoppingCart.objects.create(user=user)
