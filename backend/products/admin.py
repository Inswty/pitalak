from django import forms
from django.contrib import admin
from django.core.validators import MinValueValidator
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


class IngredientInProductInline(admin.TabularInline):
    model = IngredientInProduct
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['energy_value'].disabled = True
        self.fields['energy_value'].help_text = (
            'Рассчитывается автоматически из значений БЖУ'
        )
        # Делаем поля необязательными
        for field in ['proteins', 'fats', 'carbs']:
            self.fields[field].required = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = (
        'name',
        'category',
        'is_available',
        'image_preview',
        'price',
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
