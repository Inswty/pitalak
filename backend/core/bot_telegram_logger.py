import logging

from .tasks import send_log_to_telegram


class TelegramHandler(logging.Handler):
    """Логгер, шлёт уведомления об ошибках в Telegram."""

    def emit(self, record):
        try:
            msg = self.format(record)
            send_log_to_telegram.delay(msg)
        except Exception:
            pass
