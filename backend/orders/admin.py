from django.urls import path

from django.contrib import admin, messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from users.models import Address
from .models import CartItem, Order, OrderItem, Product, ShoppingCart
from .services import OrderService


class ProductPriceAdminMixin:
    """Добавляет универсальный эндпоинт для получения цены продукта."""

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'api/get-product-price/<int:pk>/',
                self.admin_site.admin_view(self.get_product_price),
                name='admin_get_product_price',
            ),
        ]
        return custom_urls + urls

    def get_product_price(self, request, pk):
        """Возвращает цену выбранного товара для автозаполнения в инлайне."""
        product = Product.objects.filter(pk=pk).only('price').first()
        return JsonResponse({'price': product.price if product else None})


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    fields = ('product', 'quantity', 'price', 'line_total',)
    readonly_fields = ('price', 'line_total',)
    autocomplete_fields = ('product',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

    def price(self, obj):
        """Отображаем цену товара в input для JS."""
        price = obj.product.price if obj.product else ''
        html = f'<input type="text" class="vDecimalField" name="price" readonly value="{price}">'
        return mark_safe(html)
    price.short_description = 'Цена'

    def line_total(self, obj):
        """Отображаем пустую строку для новых, иначе вычисляем."""
        if obj.pk is None or obj.product is None:
            html_value = ''
        else:
            price = obj.product.price
            value = price * obj.quantity
            html_value = f'{value:,.2f}'.replace(',', ' ')
        html = f'<input type="text" class="vDecimalField" data-name="line_total" readonly value="{html_value}">'
        return mark_safe(html)
    line_total.short_description = 'Сумма'

    class Media:
        js = ('admin/js/price-autofill.js', 'admin/js/update-total-price.js',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(ProductPriceAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'item_list',)
    actions = ['create_order_from_cart']
    inlines = [CartItemInline]
    search_fields = ('user', 'user__email')
    readonly_fields = ('total_sum_display',)
    fields = ('user', 'total_sum_display',)

    def total_sum_display(self, obj):
        """Отображает общую сумму корзины."""
        if obj is None or not obj.pk:
            return format_html('<div id="id_total_price" class="readonly">0,00</div>')

        total = sum(
            (item.product.price if item.product else 0) * item.quantity
            for item in obj.items.all()
        )
        formatted = f'{total:,.2f}'.replace(',', ' ')
        return format_html('<div id="id_total_price" class="readonly">{}</div>', formatted)

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


class ProductInOrderInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('line_total',)
    autocomplete_fields = ('product',)

    def line_total(self, obj):
        value = obj.price * obj.quantity if obj.pk else 0
        formatted = f'{value:,.2f}'.replace(',', ' ')
        return format_html(
            '<input type="text" readonly class="vDecimalField" value="{}" />',
            formatted
        )
    line_total.short_description = 'Сумма'

    class Media:
        js = ('admin/js/price-autofill.js',)


@admin.register(Order)
class OrderAdmin(ProductPriceAdminMixin, admin.ModelAdmin):
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
    list_display_links = ('order_number', 'user')  # Кликабельные поля
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
                self.admin_site.admin_view(self.get_addresses_for_user),
                name='admin_addresses_for_user',
            ),
        ]
        return custom_urls + urls

    def get_addresses_for_user(self, request):
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

    class Media:
        js = ('admin/js/address-filter.js',
              'admin/js/update-total-price.js',
              )
