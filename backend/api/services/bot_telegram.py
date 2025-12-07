import logging

from django.conf import settings
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID

bot = TeleBot(token=TELEGRAM_TOKEN)


# Проверяем переменные окружения при импорте
missing_tokens = []
if not TELEGRAM_TOKEN:
    missing_tokens.append('BOT_TOKEN')
if not TELEGRAM_CHAT_ID:
    missing_tokens.append('TELEGRAM_CHAT_ID')

if missing_tokens:
    error_msg = (
        f'Отсутствуют переменные окружения: {", ".join(missing_tokens)}'
    )
    logger.critical(error_msg)
    raise RuntimeError(error_msg)


def send_telegram_message(message):
    """Отправляет сообщение в Telegram-чат."""
    logger.info('Отправка сообщения в чат-Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, f'Pitalak:\n{message}')
    except ApiTelegramException as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')
    else:
        logger.debug('Сообщение успешно отправлено')
        return True
