// Динамическая фильтрация адресов в форме заказа
document.addEventListener('DOMContentLoaded', function() {
    const addressSelect = document.querySelector('#id_address');
    const userContainer = document.querySelector('.field-user');
    if (!addressSelect || !userContainer) return;

    console.log('JS для фильтрации адресов загружен!');

    const userSelect = () => document.querySelector('#id_user');
    let lastUserId = userSelect()?.value || null;

    function clearAddresses() {
        addressSelect.innerHTML = '<option value="">------------</option>';
        addressSelect.value = '';
    }

    async function loadAddresses(userId, reset = true) {
        if (!userId) return;

        try {
            const response = await fetch(`/admin/orders/order/api/addresses/?user_id=${userId}`, {
                credentials: 'same-origin',
                cache: 'no-store' // Отключаем браузерный кэш
            });
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            if (reset) fillAddresses(data);
        } catch (err) {
            console.error('Ошибка при загрузке адресов:', err);
        }
    }

    function fillAddresses(addresses) {
        clearAddresses();
        for (const addr of addresses) {
            const opt = document.createElement('option');
            opt.value = addr.id;
            opt.textContent = addr.text;
            addressSelect.appendChild(opt);
        }
    }

    // Наблюдаем за сменой пользователя
    const observer = new MutationObserver(() => {
        const user = userSelect();
        if (!user) return;

        const userId = user.value;
        if (userId !== lastUserId) {
            lastUserId = userId;
            clearAddresses();
        }
    });

    observer.observe(userContainer, { childList: true, subtree: true });

    // Подгружаем адреса при фокусе на поле адреса
    addressSelect.addEventListener('focus', () => {
        const user = userSelect();
        if (user && user.value) {
            loadAddresses(user.value);
        }
    });

    // При редактировании заказа — подгружаем сразу
    const initialUser = userSelect();
    if (initialUser && initialUser.value) {
        lastUserId = initialUser.value;
        loadAddresses(initialUser.value, false);
    }
});
