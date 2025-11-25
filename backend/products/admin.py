from decimal import Decimal

import nested_admin
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import NumberInput
from django.forms.models import BaseInlineFormSet
from django.http import JsonResponse
from django.urls import path
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


class NutrientInIngredientInlineFormSet(BaseInlineFormSet):
    """Проверяет, что сумма нутриентов не превышает 100 г."""

    def clean(self):
        super().clean()
        total = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                total += form.cleaned_data.get('amount_per_100g', 0)
        if total > 100:
            raise ValidationError(
                'Сумма нутриентов не может быть больше 100 г '
                'на 100 г ингредиента.'
            )


class NutrientInIngredientInline(admin.TabularInline):
    model = NutrientInIngredient
    formset = NutrientInIngredientInlineFormSet
    extra = 1
    autocomplete_fields = ('nutrient',)
    readonly_fields = ('nutrient_measurement_unit',)

    # Возвращаем measurement_unit из связанного объекта Nutrient
    @admin.display(description='Единица измерения')
    def nutrient_measurement_unit(self, obj):
        return obj.nutrient.measurement_unit

    class Media:
        js = ('admin_extensions/js/nutrient-units.js',)


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
    list_display = (
        'name',
        'proteins',
        'fats',
        'carbs',
        'energy_value'
    )
    search_fields = ('name',)
    ordering = ('name',)
    form = IngredientForm
    inlines = (NutrientInIngredientInline,)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'api/get-measurement_unit/<int:pk>/',
                self.admin_site.admin_view(self.get_measurement_unit),
                name='get_measurement_unit',
            ),
        ]
        return custom_urls + urls

    def get_measurement_unit(self, request, pk):
        """Возвращает ед.измерения нутриента для автозаполнения в инлайне."""
        nutrient = (Nutrient.objects.filter(pk=pk)
                    .only('measurement_unit').first())
        return JsonResponse({'measurement_unit': nutrient.measurement_unit
                             if nutrient else None})


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


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = '__all__'

    def clean_image(self):
        """Не позволяет сохранить пустую форму изображения."""
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError(
                'Выберете файл или удалите пустую строку'
            )
        return image


class ProductImageInline(nested_admin.NestedTabularInline):
    """Уберем clear_checkbox из ImageInline."""

    model = ProductImage
    form = ProductImageForm
    fields = ('image_preview', 'image', 'order')
    readonly_fields = ('image_preview',)
    extra = 1
    sortable_field_name = 'order'

    class Media:
        js = ('admin_extensions/js/image-preview.js',)
        css = {
            'all': ('admin_extensions/'
                    'css/hide-clear-checkbox.css',)
        }


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


@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
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
    search_fields = ('name',)
    ordering = ('-id',)
    form = ProductForm
    fieldsets = (
        (None, {
            'fields': (
                'name', 'category', 'nutrition_mode',
                'proteins', 'fats', 'carbs', 'energy_value', 'description',
                'price', 'is_available', 'weight',
            )
        }),
    )
    inlines = (ProductImageInline, IngredientInProductInline)

    class Media:
        js = ('admin_extensions/js/pfc-ev-calculator.js',)

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
