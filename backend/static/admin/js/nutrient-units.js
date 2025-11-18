// Автозаполняет единицы измерения нутриентов в инлайне админки ингредиента
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
            console.log('nutrient-units.js активен');

            // Для autocomplete_fields ловим изменения
            $(document).on('change', 'select[name$="-nutrient"]', function() {
                const $row = $(this).closest('tr'); // строка инлайна
                const nutrientId = $(this).val();
                console.log('Выбран нутриент:', nutrientId)
                const $unitTd = $row.find('td.field-nutrient_measurement_unit > p');

                if (!nutrientId) {
                    $unitTd.text(''); // очищаем
                    return;
                }

                $.ajax({
                    url: '/admin/products/ingredient/api/get-measurement_unit/' + nutrientId + '/',
                    method: 'GET',
                    dataType: 'json',
                    success: function(data) {
                        console.log('Получена ед.изм:', data);
                        if (data.measurement_unit !== undefined && data.measurement_unit !== null) {
                            $unitTd.text(data.measurement_unit);
                        }
                    },
                    error: function(err) {
                        console.error('Ошибка получения ед.изм:', err);
                    }
                });
            });
        });
    }

    init();
})();
