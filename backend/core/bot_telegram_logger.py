import logging
from textwrap import shorten

from .tasks import send_log_to_telegram

MAX_TG_MESSAGE_LENGTH = 300  # Лимит симоолов telegram сообщения в log


class TelegramHandler(logging.Handler):
    """Логгер, шлёт уведомления об ошибках в Telegram."""

    def emit(self, record):
        try:
            msg = self.format(record)
            msg = shorten(
                msg, width=MAX_TG_MESSAGE_LENGTH, placeholder='\n…(truncated)'
            )
            send_log_to_telegram.delay(msg)
        except Exception:
            pass
