from decimal import Decimal

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import NumberInput
from django.forms.models import BaseInlineFormSet
from django.utils.html import format_html

from .models import (
    Category, Ingredient, IngredientInProduct, Nutrient, NutrientInIngredient,
    Product
)


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


class IngredientInProductInline(admin.TabularInline):
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


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
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


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'price': NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['energy_value'].disabled = False
        self.fields['energy_value'].help_text = (
            'Рассчитывается автоматически из значений БЖУ'
        )
        # Делаем поля необязательными
        for field in ['proteins', 'fats', 'carbs']:
            self.fields[field].required = False

    def clean(self):
        """Если NULL -> то 0."""
        cleaned_data = super().clean()
        for field in ['proteins', 'fats', 'carbs']:
            if not cleaned_data.get(field):
                cleaned_data[field] = Decimal('0.0')
        return cleaned_data


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
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
    inlines = (IngredientInProductInline,)
    search_fields = ('name',)
    ordering = ('-id',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        (None, {
            'fields': (
                'name', 'category', 'nutrition_mode',
                'proteins', 'fats', 'carbs', 'energy_value', 'description',
                'price', 'is_available', 'image', 'image_preview', 'weight',
            )
        }),
    )

    class Media:
        js = ('admin/js/admin_product.js',)

    @admin.display(description='Ингредиенты')
    def ingredients_list(self, obj):
        return ', '.join(
            [ingredient.name for ingredient in obj.ingredients.all()]
        )

    @admin.display(description='Превью')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50">', obj.image.url
            )
        return 'No image'
