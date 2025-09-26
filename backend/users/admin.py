from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

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
    extra = 0


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
    list_filter = ('is_superuser', 'is_active', 'phone_verified')
    ordering = ('phone',)

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Personal info', {'fields': ('name', 'last_name', 'email')}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'phone_verified'
        )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'phone', 'email', 'password1', 'password2'),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'locality', 'street', 'house', 'flat', 'floor', 'added'
    )
    readonly_fields = ('user',)
    search_fields = ('locality', 'street', 'house', 'flat')
    ordering = ('-added',)
