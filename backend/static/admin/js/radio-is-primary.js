// Ограничивает выбор "Основной адрес" только одной радиокнопкой
document.addEventListener('change', function (event) {
    if (event.target.name.endsWith('-is_primary')) {
        document.querySelectorAll('input[name$="-is_primary"]').forEach(input => {
            if (input !== event.target) {
                input.checked = false;
            }
        });
    }
});
