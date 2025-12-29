import logging
from textwrap import shorten

from .constants import MAX_TG_LOG_MESSAGE_LENGTH
from .tasks import send_log_to_telegram


class TelegramHandler(logging.Handler):
    """Логгер, шлёт уведомления об ошибках в Telegram."""

    def emit(self, record):
        try:
            msg = self.format(record)
            msg = shorten(
                msg, width=MAX_TG_LOG_MESSAGE_LENGTH,
                placeholder='\n…(truncated)'
            )
            send_log_to_telegram.delay(msg)
        except Exception:
            pass
