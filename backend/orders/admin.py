from django.urls import path

from django.contrib import admin, messages
from django.http import JsonResponse
from django.shortcuts import redirect

from users.models import Address
from .models import CartItem, Order, OrderItem, Product, ShoppingCart
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

    class Media:
        js = ('admin/js/orderitem-price-autofill.js',)


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
    autocomplete_fields = ('user',)
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

    def get_form(self, request, obj=None, **kwargs):
        """
        Настраивает форму заказа в админке.

        Queryset поля 'address' ограничивается адресами выбранного пользователя
        (или пустой, если пользователь ещё не выбран).
        JS динамически подгружает адреса при выборе пользователя.
        """
        form = super().get_form(request, obj, **kwargs)
        # Определяем user_id
        user_id = None
        if request.method == 'POST':
            user_id = request.POST.get('user') or getattr(obj, 'user_id', None)
        elif obj:
            user_id = obj.user_id
        # Формируем queryset адресов
        if user_id:
            form.base_fields['address'].queryset = Address.objects.filter(
                user_id=user_id
            )
        else:
            form.base_fields['address'].queryset = Address.objects.none()
        # Отключаем кнопки add/change/delete/view
        for attr in ['can_add_related', 'can_change_related',
                     'can_delete_related', 'can_view_related']:
            setattr(form.base_fields['address'].widget, attr, False)
        return form

    def get_urls(self):
        """
        Расширяем маршруты админки заказов.

        Добавляем API для подгрузки адресов пользователя и цен продуктов.
        """

        urls = super().get_urls()
        custom_urls = [
            path(
                'api/addresses/',
                self.admin_site.admin_view(self.addresses_for_user),
                name='admin_addresses_for_user',
            ),
            path(
                'api/get-product-price/<int:pk>/',
                self.admin_site.admin_view(self.get_product_price),
                name='admin_get_product_price',
            ),
        ]
        return custom_urls + urls

    def addresses_for_user(self, request):
        """Возвращает список адресов, принадлежащих выбранному пользователю."""
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse([], safe=False)

        addresses = Address.objects.filter(user_id=user_id)
        data = [
            {
                'id': a.id,
                'text': ', '.join(filter(None, [
                    a.locality,
                    f'ул. {a.street}',
                    f'д. {a.house}' if a.house else None,
                    f'кв. {a.flat}' if a.flat else None,
                    f'эт. {a.floor}' if a.floor else None,
                ]))
            }
            for a in addresses
        ]
        return JsonResponse(data, safe=False)

    def get_product_price(self, request, pk):
        """Возвращает цену выбранного товара для автозаполнения в инлайне."""
        product = Product.objects.filter(pk=pk).only('price').first()
        return JsonResponse({'price': product.price if product else None})

    class Media:
        js = ('admin/js/address-filter.js',)
