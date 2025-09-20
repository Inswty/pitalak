import requests
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class TargetSMSClient:
    def __init__(self):
        self.login = settings.SMS_PROVIDER_LOGIN
        self.password = settings.SMS_PROVIDER_PASSWORD
        self.sender = settings.SMS_PROVIDER_SENDER
        self.base_url = settings.SMS_PROVIDER_API_URL
        self.timeout = 10

    def send_sms(self, phone: str, otp: str):
        """Отправка SMS с обработкой ошибок."""
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
                    "text": settings.OTP_TEXT.format(otp=otp),
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
                self.base_url,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json; charset=utf-8"
                }
            )
            response.raise_for_status()

            result = response.json()
            if result.get('status') == 'send':
                logger.info('SMS отправлено на %s, message_id=%s',
                            phone, result.get('message_id'))
                return result.get('message_id')
            else:
                logger.error('Ошибка SMS провайдера для %s: %s',
                             phone, result)
                return None

        except requests.exceptions.Timeout:
            logger.error('Таймаут при отправке SMS на %s', phone)
            return None
        except requests.exceptions.ConnectionError:
            logger.error('Ошибка соединения с SMS провайдером для %s', phone)
            return None
        except requests.exceptions.HTTPError as e:
            logger.error('HTTP ошибка при отправке SMS на %s: %s', phone, e)
            return None
        except requests.exceptions.RequestException as e:
            logger.error('Ошибка сети при отправке SMS на %s: %s', phone, e)
            return None
        except ValueError as e:
            logger.error('Невалидный JSON ответ от SMS провайдера для %s: %s',
                         phone, e)
            return None
