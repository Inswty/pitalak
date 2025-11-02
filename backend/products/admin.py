from decimal import Decimal

import nested_admin
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import NumberInput
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from .models import (
    Category, Ingredient, IngredientInProduct, Nutrient, NutrientInIngredient,
    Product, ProductImage
)


class NutritionFieldsMixin:
    """Добавляет общую логику для форм с полями proteins, fats, carbs."""

    NUTRITION_FIELDS = ['proteins', 'fats', 'carbs']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем поля необязательными
        for field in self.NUTRITION_FIELDS:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        for field in self.NUTRITION_FIELDS:
            if cleaned_data.get(field) is None:
                cleaned_data[field] = Decimal('0.0')
        return cleaned_data


class NutrientInIngredientInline(admin.TabularInline):
    model = NutrientInIngredient
    extra = 1
    autocomplete_fields = ('nutrient',)
    readonly_fields = ('nutrient_measurement_unit',)

    # возвращаем measurement_unit из связанного объекта Nutrient
    @admin.display(description='Единица измерения')
    def nutrient_measurement_unit(self, obj):
        return obj.nutrient.measurement_unit


class ProductIngredientInlineFormSet(BaseInlineFormSet):
    """Проверяет, что сумма ингредиентов не превышает 100 г."""

    def clean(self):
        super().clean()
        total = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                total += form.cleaned_data.get('amount', 0)
        if total > 100:
            raise ValidationError(
                'Сумма ингредиентов не может быть больше 100 г '
                'на 100 г продукта.'
            )


class IngredientInProductInline(nested_admin.NestedTabularInline):
    model = IngredientInProduct
    formset = ProductIngredientInlineFormSet
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
        'rda',
    )
    search_fields = ('name',)
    ordering = ('name',)


class IngredientForm(NutritionFieldsMixin, forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = '__all__'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    form = IngredientForm
    list_display = (
        'name',
        'proteins',
        'fats',
        'carbs',
        'energy_value'
    )
    inlines = (NutrientInIngredientInline,)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
        'is_available',
    )
    list_editable = ('is_available',)
    search_fields = ('name',)
    ordering = ('name',)


class ProductForm(NutritionFieldsMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {'price': NumberInput(attrs={'min': 0})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['energy_value'].disabled = False
        self.fields['energy_value'].help_text = (
            'Рассчитывается автоматически из значений БЖУ'
        )


class ProductImageInline(nested_admin.NestedTabularInline):
    """Уберем clear_checkbox из ImageInline."""

    model = ProductImage
    extra = 1
    fields = ('image_preview', 'image', 'order')
    readonly_fields = ('image_preview',)
    sortable_field_name = 'order'

    class Media:
        js = ('admin/js/image-preview.js',)
        css = {
            'all': ('admin/css/hide-clear-checkbox.css',)
        }


@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
    form = ProductForm
    list_display = (
        'name',
        'category',
        'is_available',
        'image_preview',
        'price',
        'weight',
        'ingredients_list',
    )
    list_editable = (
        'price', 'is_available',
    )
    inlines = (ProductImageInline, IngredientInProductInline)
    search_fields = ('name',)
    ordering = ('-id',)
    fieldsets = (
        (None, {
            'fields': (
                'name', 'category', 'nutrition_mode',
                'proteins', 'fats', 'carbs', 'energy_value', 'description',
                'price', 'is_available', 'weight',
            )
        }),
    )

    class Media:
        js = ('admin/js/pfc-ev-calculator.js',)

    @admin.display(description='Ингредиенты')
    def ingredients_list(self, obj):
        return ', '.join(
            [ingredient.name for ingredient in obj.ingredients.all()]
        )

    @admin.display(description='Превью')
    def image_preview(self, obj):
        first_image = obj.images.first()  # Берем первый related ProductImage
        if first_image and first_image.image:
            return format_html(
                '<img src="{}" width="60" style="border-radius:4px;">',
                first_image.image.url
            )
        return 'No image'
