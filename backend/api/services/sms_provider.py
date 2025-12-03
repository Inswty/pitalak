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
        phone = phone.lstrip('+')
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
                json=payload,  # requests сериализует в JSON
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json; charset=utf-8"
                }
            )
            response.raise_for_status()   # Проверка HTTP-ошибок (4xx, 5xx)
            # Возвращаем десериализованный JSON-ответ
            result = response.json().get('sms', [])
            if not result:
                # Провайдер не вернул массив 'sms' - это ошибка
                logger.error(
                    'Ошибка SMS провайдера для %s: Невалидный формат ответа - '
                    'нет массива "sms". %s', phone, result
                )
                return None
            message_info = result[0]
            if message_info.get('action') == 'send':
                message_id = message_info.get('id_sms')
                logger.info('SMS отправлено на %s, message_id=%s',
                            phone, message_id)
                return message_id
            else:
                action_status = message_info.get('action', 'N/A')
                logger.error('Ошибка SMS провайдера для %s: Статус "%s".'
                             ' Ответ: %s', phone, action_status, result)
                return None

        except requests.exceptions.RequestException as e:
            status_code = getattr(
                getattr(e, 'response', None), 'status_code', 'N/A'
            )
            logger.error('Ошибка сети/HTTP (%s) при отправке SMS на %s: %s',
                         status_code, phone, e)
            return None
        except ValueError as e:
            logger.error('Невалидный JSON ответ от SMS провайдера для %s: %s',
                         phone, e)
            return None

    def get_balance(self):
        """
        Запрос баланса.

        Возвращает:
            dict: JSON-ответ от провайдера
            (либо с ключом 'money', либо с ключом 'error').
        """
        payload = {
            "security": {
                "login": self.login,
                "password": self.password
            },
            "type": "balance"
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
            return response.json()

        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error('Ошибка при запросе баланса SMS: %s', e)
            return None
