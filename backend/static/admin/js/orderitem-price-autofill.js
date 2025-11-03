//Автозаполняет цену товара в инлайне админки при выборе продукта
(function() {
    // Ждём, пока загрузится admin и его jQuery
    function init() {
        if (typeof django === 'undefined' || typeof django.jQuery === 'undefined') {
            console.warn('Ожидаем загрузку django.jQuery...');
            setTimeout(init, 100);
            return;
        }

        const $ = django.jQuery;

        $(document).ready(function() {
            console.log('orderitem-price-autofill.js активен');

            // Слушаем изменения поля "product" в инлайне
            $(document).on('change', 'select[name$="-product"]', function() {
                const $row = $(this).closest('.dynamic-items');
                const productId = $(this).val();
                const $priceInput = $row.find('input[name$="-price"]');

                console.log('Выбран продукт:', productId);

                if (!productId) return;

                $.ajax({
                    url: '/admin/orders/order/api/get-product-price/' + productId + '/',
                    method: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('Цена получена:', data);
                        if (data.price !== undefined && data.price !== null) {
                            $priceInput.val(data.price).trigger('change');
                        }
                    },
                    error: function(err) {
                        console.error('Ошибка при запросе цены:', err);
                    }
                });
            });
        });
    }

    init();
})();
