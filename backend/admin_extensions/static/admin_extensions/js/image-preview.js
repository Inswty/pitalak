// Динамическая загрузка превью изображения
document.addEventListener('change', function (event) {
    const input = event.target;

    // Проверяем, что изменилось именно поле загрузки файла
    if (!input.matches('input[type="file"][id^="id_images-"]')) return;

    const row = input.closest('tr.djn-tr');
    if (!row) return;

    const previewTd = row.querySelector('td.field-image_preview');
    if (!previewTd) return;

    const file = input.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        // Проверяем, есть ли уже <p><img>
        let p = previewTd.querySelector('p');
        if (!p) {
            p = document.createElement('p');
            previewTd.appendChild(p);
        }

        // Добавляем/обновляем <img> с теми же стилями
        let img = p.querySelector('img');
        if (!img) {
            img = document.createElement('img');
            img.style.height = '80px';
            img.style.borderRadius = '4px';
            p.appendChild(img);
        }

        img.src = e.target.result;
    };

    reader.readAsDataURL(file);
});
