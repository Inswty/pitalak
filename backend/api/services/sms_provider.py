import requests
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class TargetSMSClient:
    """API клиент TargetSMS."""

    def __init__(self):
        self.login = settings.SMS_PROVIDER_LOGIN
        self.password = settings.SMS_PROVIDER_PASSWORD
        self.sender = settings.SMS_PROVIDER_SENDER
        self.base_url = settings.SMS_PROVIDER_API_URL
        self.timeout = 25

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
                # Провайдер не вернул массив 'sms'
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


class TelegramClient:
    """API клиент Telegram Gateway."""

    def __init__(self):
        self.tgm_url = settings.MSG_TELEGRAM_API_URL
        self.tgm_token = settings.MSG_TELEGRAM_API_TOKEN
        self.tgm_check_url = settings.MSG_CAN_SEND_ENDPOINT
        self.timeout = 25

    def prepare_send(self, phone: str) -> str | None:
        phone = phone.lstrip('+')
        payload = {
            'phone_number': phone,
        }
        try:
            response = requests.post(
                self.tgm_check_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json; charset=utf-8',
                    'Authorization': f'Bearer {self.tgm_token}',
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            # 1. Проверка флага ok
            if not data.get('ok'):
                logger.info(
                    'Telegram Gateway: отправка не доступна для %s: %s',
                    phone,
                    data,
                )
                return None

            # 2. Проверка result
            result = data.get('result')
            if not isinstance(result, dict):
                logger.error(
                    'Telegram Gateway invalid check response for %s: %s',
                    phone,
                    data,
                )
                return None

            # 3. Извлекаем request_id
            request_id = result.get('request_id')
            if not request_id:
                logger.error(
                    'Telegram Gateway отсутствует request_id в ответе %s: %s',
                    phone,
                    data,
                )
                return None

            logger.debug(
                'Telegram Gateway позволяет отправлять на %s, request_id=%s',
                phone,
                request_id,
            )
            return request_id

        except requests.exceptions.RequestException as e:
            status_code = getattr(
                getattr(e, 'response', None), 'status_code', 'N/A'
            )
            logger.error(
                'Telegram Gateway check HTTP error (%s) for %s: %s',
                status_code,
                phone,
                e,
            )
            return None

        except ValueError as e:
            logger.error(
                'Telegram Gateway returned invalid JSON during check %s: %s',
                phone,
                e,
            )
            return None

    def send_sms(self, phone: str, otp: str, request_id: str) -> str | None:
        phone = phone.lstrip('+')

        payload = {
            'phone_number': phone,
            'code': otp,
            'ttl': 30,
            'request_id': request_id,
        }

        try:
            response = requests.post(
                self.tgm_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json; charset=utf-8',
                    'Authorization': f'Bearer {self.tgm_token}',
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            # 1. Базовая валидация
            if not data.get('ok'):
                logger.error(
                    'Telegram Gateway вернул ok=false для %s: %s',
                    phone,
                    data,
                )
                return None

            result = data.get('result')
            if not isinstance(result, dict):
                logger.error(
                    'Telegram Gateway отсутствует result для %s: %s',
                    phone,
                    data,
                )
                return None

            # 2. Проверка статуса доставки
            delivery_status = result.get('delivery_status', {})
            status = delivery_status.get('status')

            if status != 'sent':
                logger.error(
                    'Telegram Gateway SMS не отправлено %s.'
                    'Status=%s. Response=%s',
                    phone,
                    status,
                    data,
                )
                return None

            # 3. request_id — идентификатор сообщения
            request_id = result.get('request_id')
            if not request_id:
                logger.error(
                    'Telegram Gateway отсутствует request_id для %s: %s',
                    phone,
                    data,
                )
                return None

            logger.info(
                'Telegram Gateway SMS отправлено на %s, request_id=%s',
                phone,
                request_id,
            )
            return request_id

        except requests.exceptions.RequestException as e:
            status_code = getattr(
                getattr(e, 'response', None), 'status_code', 'N/A'
            )
            logger.error(
                'Telegram Gateway HTTP error (%s) for %s: %s',
                status_code,
                phone,
                e,
            )
            return None

        except ValueError as e:
            logger.error(
                'Telegram Gateway вернул недействительный JSON для %s: %s',
                phone,
                e,
            )
            return None
