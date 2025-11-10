// Динамически пересчитывает суммы заказа и позиций в админке
(function() {
    function waitForJQuery(callback) {
        if (typeof django !== 'undefined' && typeof django.jQuery !== 'undefined') {
            callback(django.jQuery);
        } else {
            setTimeout(() => waitForJQuery(callback), 200);
        }
    }

    waitForJQuery(function($) {
        console.log('django.jQuery загружен, инициализация скрипта...');

        // Поиск поля общей суммы
        function findTotalField() {
            const input = $('#id_total_price');
            if (input.length) return { type: 'input', el: input };

            const div = $('.field-total_price div.readonly').first();
            if (div.length) return { type: 'div', el: div };

            const p = $('.field-total_price p').first();
            if (p.length) return { type: 'p', el: p };

            return null;
        }

        const found = findTotalField();
        if (!found) {
            console.warn('Не найдено поле total_price');
            return;
        }

        const originalColor = found.el.css('color');

        // Пересчёт сумм
        function recalcTotal() {
            let total = 0;

            $('tr.form-row[class*="dynamic-"]').each(function() {
                const $row = $(this);
                const isDeleted = $row.find('input[name$="-DELETE"]').prop('checked');
                if (isDeleted) return;

                const price = parseFloat($row.find('input[name$="-price"]').val()) || 0;
                const quantity = parseFloat($row.find('input[name$="-quantity"]').val()) || 0;
                const lineTotal = price * quantity;

                // Отображаем сумму по строке (если есть <p> или <div>)
                const $lineField = $row.find('.field-line_total input');
                if ($lineField.length) {
                    $lineField.val(lineTotal.toLocaleString('ru-RU', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    }));
                }
                $lineField.css('color', '#808080'); // серый текст

                total += lineTotal;
            });

            const formatted = total.toLocaleString('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            if (found.type === 'input') found.el.val(formatted);
            else found.el.text(formatted);

            // Подсветка при изменении
            found.el.css('color', 'red');
            if (found.highlightTimer) clearTimeout(found.highlightTimer);
            found.highlightTimer = setTimeout(() => {
                found.el.css('color', originalColor);
            }, 800);
        }

        // Слушатели
        $(document).on('input change', 'input[name$="-price"], input[name$="-quantity"]', recalcTotal);

        $(document).on('click', '.inline-deletelink', function(e) {
            e.preventDefault();
            const $row = $(this).closest('tr');
            const $deleteCheckbox = $row.find('input[name$="-DELETE"]');
            if ($deleteCheckbox.length) {
                $deleteCheckbox.prop('checked', true);
                $row.hide();
            }
            recalcTotal();
        });

        $(document).on('formset:added', function() {
            recalcTotal();
        });

        $(document).ready(recalcTotal);
    });
})();
