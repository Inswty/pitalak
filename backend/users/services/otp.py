import random

from core.constants import OTP_LENGTH


def generate_otp(length=OTP_LENGTH):
    """Генерация случайного OTP заданной длины."""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])
