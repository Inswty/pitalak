import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.urls import reverse

logger = logging.getLogger(__name__)

SMS_BALANCE_CACHE_KEY = 'sms_provider_balance'


@staff_member_required
def refresh_sms_balance(request):
    """Очищает ключ кеша баланса и обновляет страницу."""

    cache.delete(SMS_BALANCE_CACHE_KEY)

    logger.info('Принудительное обновление баланса - '
                'ключ кэша удален: sms_provider_balance;)'
                )
    return HttpResponseRedirect(
        request.GET.get('next') or reverse('admin:index')
    )
