document.addEventListener('DOMContentLoaded', function() {
    const userSelect = document.querySelector('#id_user');
    const addressSelect = document.querySelector('#id_address');

    if (!userSelect || !addressSelect) return;

    userSelect.addEventListener('change', function() {
        const userId = this.value;
        addressSelect.innerHTML = '<option value="">---------</option>';

        if (!userId) return;

        fetch(`/admin/api/addresses/?user_id=${userId}`)
            .then(response => response.json())
            .then(data => {
                data.forEach(addr => {
                    const opt = document.createElement('option');
                    opt.value = addr.id;
                    opt.textContent = addr.text;
                    addressSelect.appendChild(opt);
                });
            });
    });
});
