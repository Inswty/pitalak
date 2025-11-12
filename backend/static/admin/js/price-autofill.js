// Автозаполняет цену товара в инлайне админки при выборе продукта
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
            console.log('price-autofill.js активен');

            // Слушаем изменения поля "product" в инлайне
            $(document).on('change', 'select[name$="-product"]', function() {
                console.log('[price-autofill] Событие change product');

                const $select = $(this);
                const productId = $select.val();
                console.log('Выбран productId:', productId);

                if (!productId) return;

                // Определяем строку инлайна (работает и в заказах, и в корзине)
                const $row = $select.closest('tr, .dynamic-items, .dynamic-cartitem');
                console.log('Найдена строка инлайна:', $row);

                // Ищем поле для цены
                let $priceInput = $row.find('input[name$="-price"], input.fake-price');

                // Если не найдено — создаём новое поле
                if (!$priceInput.length) {
                    console.log('Input для цены не найден, создаём динамически');
                    const $cell = $row.find('td.field-price_display, td.field-price');
                    if ($cell.length) {
                        // добавляем name="price", чтобы старый JS пересчёта видел изменение
                        $cell.html('<input type="text" class="vDecimalField fake-price" name="price" readonly>');
                        $priceInput = $cell.find('input.fake-price');
                        console.log('Создан input.fake-price:', $priceInput);
                    }
                }

                // Формируем URL запроса
                let path = window.location.pathname.replace(/\/\d+\/change\/?$/, '/');
                const url = path + 'api/get-product-price/' + productId + '/';
                console.log('URL запроса цены:', url);

                // Получаем цену
                $.ajax({
                    url: url,
                    method: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('Response от сервера:', data);
                        if (data.price !== undefined && data.price !== null) {
                            $priceInput.val(data.price).trigger('change');
                            console.log('Цена подставлена:', data.price);
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
