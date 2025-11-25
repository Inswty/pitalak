// Динамический подсчет PFC, EV, изменении полей при выборе режимов
document.addEventListener('DOMContentLoaded', function () {
    const modeSelect = document.querySelector('#id_nutrition_mode');
    const names = ['proteins', 'fats', 'carbs', 'energy_value'];
  
    // Кешируем строки и инпуты
    const rows = {};
    const inputs = {};
    names.forEach(name => {
      rows[name] = document.querySelector(`.form-row.field-${name}`);
      inputs[name] = rows[name] ? rows[name].querySelector('input') : null;
    });

    function calculateEnergyValue() {
        if (modeSelect.value !== 'manual') return;
    
        const proteins = parseFloat(inputs.proteins?.value) || 0;
        const fats = parseFloat(inputs.fats?.value) || 0;
        const carbs = parseFloat(inputs.carbs?.value) || 0;
    
        const energyValue = Math.round(proteins * 4 + fats * 9 + carbs * 4);
        if (inputs.energy_value) {
          inputs.energy_value.value = energyValue || '0';
        }
      }
  
    // mode: 'none' | 'auto' | 'manual'
    // reset = true когда пользователь поменял режим (тогда сбрасываем значения)
    function applyMode(mode, reset = false) {
      names.forEach(name => {
        const row = rows[name];
        const input = inputs[name];
        if (!row || !input) return;
  
        if (reset) {
          // Сбрасываем только при явной смене режима
          input.value = '';
        }
  
        if (mode === 'none') {
          row.style.display = 'none';
          input.readOnly = false;   // Оставляем отправляемым, но скрываем
          input.required = false;
          input.value = '0';
  
        } else if (mode === 'auto') {
          row.style.display = '';
          // Делаем только для просмотра — readOnly (будет отправлено, но пустое при reset),
          // сервер при сохранении должен пересчитать и записать новые значения
          input.readOnly = true;
          input.required = false;
          if (!input.value) input.placeholder = '-';
          input.style.color = '#666';
  
        } else { // manual
          row.style.display = '';
          if (name === 'energy_value') {
            // energy_value показываем как readonly (вычисляется сервером)
            input.readOnly = true;
            input.required = false;
            if (!input.value) input.placeholder = '-';
          } else {
            // БЖУ редактируемы и обязательны
            input.readOnly = false;
            input.required = true;
            input.style.color = '';
            // При переключении в ручной режим -> 0, если поле было сброшено
            if (reset && !input.value) input.value = '0';
          }
        }
      });
    }
  
    if (modeSelect) {
      // Начальная инициализация — НЕ сбрасываем значения, чтобы не потерять то, что уже в базе
      applyMode(modeSelect.value, false);
  
      // При изменении режима — сбрасываем поля и применяем поведение
      modeSelect.addEventListener('change', function () {
        applyMode(modeSelect.value, true); // reset = true
      });

      // Слушаем изменения БЖУ для пересчёта
      ['proteins', 'fats', 'carbs'].forEach(name => {
        inputs[name]?.addEventListener('input', calculateEnergyValue);
      });
    }
  });
