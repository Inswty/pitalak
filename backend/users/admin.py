from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from .models import User

admin.site.unregister(Group)


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
