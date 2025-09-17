import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.constants import OTP_LENGTH

OTP_TTL = settings.OTP_TTL_SECONDS


def generate_otp():
    """Генерация случайного OTP заданной длины."""
    return ''.join([str(random.randint(0, 9)) for _ in range(OTP_LENGTH)])


def otp_expiry_time():
    """Возвращает время истечения срока действия OTP."""
    return timezone.now() + timedelta(seconds=OTP_TTL)
