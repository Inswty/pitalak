from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.urls import reverse
from django.utils.html import format_html

from .models import User, Address

admin.site.unregister(Group)


class AddressInlineFormSet(forms.BaseInlineFormSet):
    """Проверим, что не больше одного адреса отмечено как основной."""
    def clean(self):
        super().clean()
        primary_count = sum(
            1 for form in self.forms
            if form.cleaned_data.get('is_primary', False)
        )
        if primary_count > 1:
            raise ValidationError('Только один адрес может быть основным.')


class AddressInline(admin.TabularInline):
    model = Address
    formset = AddressInlineFormSet
    extra = 1

    class Media:
        css = {
            'all': ('admin/css/user-addresses.css',)
        }


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'name',
        'phone',
        'email',
        'is_superuser',
        'is_active',
        'phone_verified',
    )
    inlines = (AddressInline,)
    list_display_links = ('phone', 'name')  # кликабельные поля
    search_fields = ('phone', 'email', 'name')
    readonly_fields = ('orders_link', 'total_cost_orders')
    list_filter = ('is_superuser', 'is_active', 'phone_verified')
    ordering = ('phone',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Персональная информация', {'fields': (
            'name', 'last_name', 'email'
        )}),
        ('Разршения', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'phone_verified'
        )}),
        ('Статистика', {'fields': (
            'orders_link', 'total_cost_orders'
        )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'phone', 'email', 'password1', 'password2'),
        }),
    )

    @admin.display(description='Сумма заказов')
    def total_cost_orders(self, obj):
        """Подсчёт суммы всех закозов пользователя."""
        result = obj.orders.aggregate(total=Sum('total_price'))['total']
        if result is None:
            return '0.00 ₽'
        # Округляем до 2 знаков после запятой
        result = result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Форматируем с пробелами между тысячами
        formatted = f'{result:,.2f}'.replace(',', ' ')
        return f'{formatted} ₽'

    @admin.display(description='Заказы')
    def orders_link(self, obj):
        """Добавляем отдельную строку-ссылку на заказы пользователя."""
        count = obj.orders.count()
        if count == 0:
            return '—'
        url = (
            reverse('admin:orders_order_changelist')
            + f'?user__id__exact={obj.id}'
        )
        return format_html(
            '<a href="{}">Список заказов ({})</a>', url, count
        )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'locality', 'street', 'house', 'flat', 'floor', 'added'
    )
    search_fields = ('locality', 'street', 'house', 'flat')
    ordering = ('-added',)
