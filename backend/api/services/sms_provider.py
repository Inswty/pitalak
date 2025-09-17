import requests
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.timezone import now

from core.constants import OTP_TEXT

logger = logging.getLogger(__name__)


class TargetSMSClient:
    def __init__(self):
        self.login = settings.SMS_PROVIDER_LOGIN
        self.password = settings.SMS_PROVIDER_PASSWORD
        self.sender = settings.SMS_PROVIDER_SENDER
        self.base_url = settings.SMS_PROVIDER_API_URL

    def send_sms(self, phone: str, otp: str):
        """Отправка SMS через TargetSMS"""
        payload = {
            "security": {
                "login": self.login,
                "password": self.password
            },
            "type": "sms",
            "message": [
                {
                    "type": "sms",
                    "sender": self.sender,
                    "text": OTP_TEXT.format(otp=otp),
                    "name_delivery": "OTP Authorization",
                    "abonent": [
                        {
                            "phone": phone,
                            "number_sms": "1",
                            "client_id_sms": f"otp_{phone}_{int(
                                datetime.now().timestamp())}",
                            "validity_period": (
                                now() + timedelta(
                                    seconds=settings.OTP_TTL_SECONDS
                                )
                            ).strftime("%Y-%m-%d %H:%M"),
                        }
                    ]
                }
            ]
        }
        try:
            response = requests.post(
                self.base_url, json=payload
            )
            response.raise_for_status()
            result = response.json()
            if result.get('status') == 'ok':
                logger.info('SMS успешно отправлено на %s', phone)
                return result.get('message_id')  # Вернуть ID для отслеживания
            else:
                logger.error(
                    'Provider_SMS ошибка отправки на номер %s: %s',
                    phone, result
                )
                return None
        except requests.exceptions.RequestException as e:
            logger.error('SMS отправка не удалась на номер %s: %s', phone, e)
            return None


