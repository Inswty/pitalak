from django.contrib import admin, messages
from django.shortcuts import redirect

from .models import Order, OrderItem, ShoppingCart, CartItem
from .services import OrderService


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    autocomplete_fields = ('product',)


class ProductInOrderInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    min_num = 1
    autocomplete_fields = ('product',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_list',)
    actions = ['create_order_from_cart']
    inlines = [CartItemInline]
    search_fields = ('user', 'user__email')
    fieldsets = (
        (None, {
            'fields': (
                'user',
            )
        }),
    )

    @admin.display(description='Товары')
    def item_list(self, obj):
        return ', '.join(
            [product.name for product in obj.products.all()]
        )

    @admin.action(description='Создать заказ из корзины')
    def create_order_from_cart(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                'Можно создавать заказ только из одной корзины за раз.',
                level=messages.ERROR
            )
            return
        cart = queryset.first()
        try:
            order = OrderService.create_from_cart(
                cart, address=cart.user.addresses.first())
            self.message_user(
                request,
                f'Заказ #{order.order_number} успешно создан!',
                level=messages.SUCCESS
            )
            return redirect(f'../order/{order.id}/change/')
        except ValueError as e:
            self.message_user(request, str(e), level=messages.ERROR)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'created_at',
        'total_price',
    )
    list_editable = ('status',)
    inlines = (ProductInOrderInline,)
    readonly_fields = ('order_number', 'total_price', 'created_at',)
    list_display_links = ('order_number', 'user')  # кликабельные поля
    search_fields = (
        'order_number', 'user__email', 'user__name', 'user__phone'
    )
    list_filter = ('status',)
    autocomplete_fields = ('user', 'address')
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'created_at',
                'status',
                'address',
                'total_price',
                'comment',
            )
        }),
    )

    @admin.display(description='Товары')
    def product_list(self, obj):
        return ', '.join(
            [product.name for product in obj.products.all()]
        )
