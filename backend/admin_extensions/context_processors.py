import logging

from django.core.cache import cache
from django.conf import settings

from api.services.sms_provider import TargetSMSClient

logger = logging.getLogger(__name__)

SMS_BALANCE_CACHE_TIMEOUT = getattr(
    settings, 'SMS_BALANCE_CACHE_TIMEOUT', 43200
)

try:
    SMS_CLIENT = TargetSMSClient()
except Exception as e:
    SMS_CLIENT = None
    print(f'Не удалось инициализировать TargetSMSClient: {e}')


def get_sms_balance(request):
    """
    Контекстный процессор, использующий метод get_balance клиента.
    """
    if not settings.DEBUG:
        CACHE_KEY = 'sms_provider_balance'
        balance_display = cache.get(CACHE_KEY)

        if balance_display is None and SMS_CLIENT:
            try:
                # Вызов метода клиента
                logger.info('Запрос баланса')
                data = SMS_CLIENT.get_balance()

                if 'error' in data:
                    balance_display = f'Баланс OTP: Ошибка: {data['error']}'

                elif 'money' in data and 'value' in data['money']:
                    value = data['money']['value']
                    currency = data.get('money', {}).get('currency', 'ед.')

                    balance_display = f'Баланс OTP: {value} {currency}'

                    # Кешируем результат
                    cache.set(
                        CACHE_KEY, balance_display, SMS_BALANCE_CACHE_TIMEOUT
                    )
                    logger.info(
                        'Получен баланс от SMS-провадйера: %s', balance_display
                    )
                else:
                    balance_display = 'Баланс: Неизвестный формат ответа'

            except Exception as e:
                balance_display = (
                    f'Баланс: Критическая ошибка: {type(e).__name__}'
                )
                logger.warning(
                    'Баланс: Критическая ошибка: %s', {type(e).__name__}
                )

        elif not SMS_CLIENT:
            balance_display = (
                'Баланс: Клиент недоступен (ошибка инициализации)'
            )
            logger.warning('Баланс: Клиент недоступен (ошибка инициализации)')
        return {'SMS_PROVIDER_BALANCE': balance_display}

    # dev заглушка
    return {'SMS_PROVIDER_BALANCE': 'Баланс OTP: 1135.88 RUR'}
