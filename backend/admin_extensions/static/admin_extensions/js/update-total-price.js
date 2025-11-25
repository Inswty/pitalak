// Динамически пересчитывает суммы заказа и позиций в админке
(function() {
    function waitForJQuery(callback) {
        if (typeof django !== 'undefined' && typeof django.jQuery !== 'undefined') {
            callback(django.jQuery);
        } else {
            setTimeout(() => waitForJQuery(callback), 100);
        }
    }

    waitForJQuery(function($) {
        console.log('django.jQuery загружен, инициализация скрипта...');

        function findTotalField() {
            const input = $('#id_total_price');
            if (input.length) return { type: 'input', el: input };
            const div = $('.field-total_price div.readonly').first();
            if (div.length) return { type: 'div', el: div };
            const p = $('.field-total_price p').first();
            if (p.length) return { type: 'p', el: p };
            return null;
        }

        const totalField = findTotalField();
        if (!totalField) return;

        const originalColor = totalField.el.css('color') || 'inherit';

        function recalcTotal() {
            let total = 0;
        
            $('tr.form-row[class*="dynamic-"]').each(function() {
                const $row = $(this);
                if ($row.find('input[name$="-DELETE"]').prop('checked')) return;
        
                let price = 0;
        
                // Ищем цену только в текущей строке и строго по одному элементу
                const $priceField = $row.find('input.vDecimalField, input.fake-price, input[name$="-price"]').first();
        
                if ($priceField.length) {
                    const val = $priceField.val();
                    if (val && val.trim() !== '') {
                        price = parseFloat(val.replace(/\s/g, '').replace(',', '.')) || 0;
                    }
                }
        
                const quantity = parseFloat($row.find('input[name$="-quantity"]').val() || 0);
                const lineTotal = price * quantity;
        
                // Сумма строки
                const $lineField = $row.find('.field-line_total input, .field-line_total div');
                if ($lineField.length) {
                    const formatted = lineTotal.toLocaleString('ru-RU', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                    $lineField.val(formatted).text(formatted);
                }
        
                total += lineTotal;
            });
        
            const formattedTotal = total.toLocaleString('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        
            totalField.el.val(formattedTotal).text(formattedTotal);
        
            totalField.el.css('color', 'red');
            clearTimeout(totalField.el.data('timer'));
            totalField.el.data('timer', setTimeout(() => {
                totalField.el.css('color', originalColor);
            }, 800));
        }

        // Слушатели
        $(document).on('input change', 'input[name$="-quantity"], input[name$="-price"], input.fake-price, select[name$="-product"]', recalcTotal);
        $(document).on('formset:added formset:removed', recalcTotal);
        $(document).on('click', '.inline-deletelink', function(e) {
            e.preventDefault();
            $(this).closest('tr').find('input[name$="-DELETE"]').prop('checked', true).closest('tr').hide();
            recalcTotal();
        });

        $(document).ready(function() {
            const hasValue = totalField.el.is('input') 
                ? totalField.el.val().trim() !== '' && totalField.el.val() !== '0,00'
                : totalField.el.text().trim() !== '' && totalField.el.text() !== '0,00';

            if (hasValue) {
                console.log('Посчитано бэкендом — не трогаем');
                return;
            }

            console.log('Считаем с нуля');
            recalcTotal();
        });

    });
})();