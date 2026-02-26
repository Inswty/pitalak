import logging
from django.core.cache import cache
from django.conf import settings

from api.services.sms_provider import TargetSMSClient

logger = logging.getLogger(__name__)

SMS_BALANCE_CACHE_KEY = 'sms_provider_balance'
SMS_BALANCE_CACHE_TIMEOUT = getattr(
    settings, 'SMS_BALANCE_CACHE_TIMEOUT'
)


def get_sms_balance(request):
    """
    Контекстный процессор: Читает баланс из кеша или синхронно
    запрашивает его у провайдера при промахе.
    """
    if settings.DEBUG:
        # Dev-заглушка
        return {'SMS_PROVIDER_BALANCE': 'Баланс OTP: 1135.88 RUR (DEV)'}

    if not request.user.is_authenticated:
        return {}

    # --- Безопасное чтение из cache ---
    try:
        balance_display = cache.get(SMS_BALANCE_CACHE_KEY)
    except Exception as e:
        logger.error('Cache GET error: %s', e)
        balance_display = None

    try:
        sms_client = TargetSMSClient()
    except Exception as e:
        sms_client = None
        logger.error('Не удалось инициализировать TargetSMSClient: %s', e)

    if balance_display is None and sms_client:
        logger.info(
            'Кеш баланса SMS пуст. Выполняется синхронный запрос к провайдеру.'
        )
        try:
            data = sms_client.get_balance()
            if data is None:
                balance_display = 'Баланс OTP: Пустой ответ провайдера'
            elif 'error' in data:
                balance_display = f'Баланс OTP: Ошибка: {data["error"]}'
            elif 'money' in data and 'value' in data['money']:
                value = data['money']['value']
                currency = data.get('money', {}).get('currency', 'ед.')
                balance_display = f'Баланс OTP: {value} {currency}'

                # Кешируем результат
                try:
                    cache.set(
                        SMS_BALANCE_CACHE_KEY,
                        balance_display,
                        SMS_BALANCE_CACHE_TIMEOUT
                    )
                except Exception as e:
                    logger.error('Cache SET error: %s', e)

                logger.info(
                    'Получен баланс от SMS-провадйера: %s', balance_display
                )
            else:
                balance_display = 'Баланс: Неизвестный формат ответа'

        except Exception as e:
            # Обработка сетевых ошибок
            balance_display = (
                f'Баланс: Критическая ошибка сети/IO: {type(e).__name__}'
            )
            logger.error('Критическая ошибка при запросе баланса: %s', e)

    elif not sms_client:
        balance_display = 'Баланс: Клиент недоступен (ошибка инициализации)'
        logger.warning('Баланс: Клиент недоступен (ошибка инициализации)')

    return {'SMS_PROVIDER_BALANCE': balance_display}
