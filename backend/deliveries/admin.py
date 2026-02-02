from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Delivery, DeliveryRule


class DeliveryRuleAdminForm(forms.ModelForm):
    class Meta:
        model = DeliveryRule
        fields = '__all__'
        widgets = {
            'time_from': forms.TimeInput(attrs={'type': 'time'}),
            'time_to': forms.TimeInput(attrs={'type': 'time'}),
            'delivery_time_from': forms.TimeInput(attrs={'type': 'time'}),
            'delivery_time_to': forms.TimeInput(attrs={'type': 'time'}),
        }

    # Валидация: time_from всегда меньше time_to
    def clean(self):
        cleaned_data = super().clean()
        t_from = cleaned_data.get('time_from')
        t_to = cleaned_data.get('time_to')

        if t_from and t_to and t_from >= t_to:
            raise ValidationError(
                'Время начала периода должно быть меньше времени окончания.'
            )

        return cleaned_data


@admin.register(DeliveryRule)
class DeliveryRuleAdmin(admin.ModelAdmin):
    form = DeliveryRuleAdminForm
    list_display = (
        'name',
        'time_from',
        'time_to',
        'days_offset',
        'delivery_time_from',
        'delivery_time_to',
        'is_active',
    )
    list_editable = ('is_active',)
    search_fields = ('name',)
    ordering = ('days_offset', 'time_from')

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Условия срабатывания правила', {
            'fields': ('time_from', 'time_to')
        }),
        ('Параметры доставки', {
            'fields': ('days_offset', 'delivery_time_from', 'delivery_time_to')
        }),
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'description', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)
    ordering = ('name',)
