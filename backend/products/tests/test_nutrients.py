import pytest
from django.db.utils import IntegrityError

from products.models import Nutrient


@pytest.mark.django_db
def test_nutrient_name_uniqueness():
    """Название нутриента должно быть уникальным."""

    name = 'Магний'
    Nutrient.objects.create(name=name, measurement_unit='мг')

    with pytest.raises(IntegrityError):
        Nutrient.objects.create(name=name, measurement_unit='мг')
