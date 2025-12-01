import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

from users.otp_manager import OTPManager
from users.models import User
from .serializers import OTPRequestSerializer, OTPVerifySerializer

logger = logging.getLogger(__name__)


class SendOTPAPIView(APIView):
    """Эндпоинт для запроса отправки OTP на телефон пользователя."""

    def post(self, request, *args, **kwargs):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        # Отправка SMS
        try:
            otp = OTPManager.request_otp(phone)
        except Throttled as e:
            # Вернем 429 с wait
            return Response(
                {'detail': e.detail, 'wait': e.wait},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except Exception as e:
            # Ловим ошибки, не связанные с Redis
            logger.error('Критическая ошибка менеджера OTP: %s', e)
            raise ValidationError({'detail': 'Не удалось отправить OTP'})
        if settings.DEBUG:
            # Отображаем OTP только режиме разработки
            print(f'DEV MODE: OTP на номер {phone}: {otp}')

        logger.info('Запрос OTP принят для %s', phone)
        return Response({
            'detail': 'OTP запрошен. Проверьте ваш телефон.',
            'TTL': settings.OTP_TTL_SECONDS
        }, status=status.HTTP_200_OK)


class VerifyOTPAPIView(APIView):
    """Эндпоинт для проверки OTP и выдачи JWT-токенов."""

    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']
        otp = serializer.validated_data['otp']

        is_valid, message = OTPManager.verify_otp(phone, otp)
        if not is_valid:
            raise ValidationError({'detail': message})

        user = self._get_or_create_user(phone)
        token = self._generate_token(user)
        return Response(token, status=status.HTTP_200_OK)

    def _get_or_create_user(self, phone: str):
        """Создание нового пользователя или получение существующего."""
        user, created = User.objects.get_or_create(phone=phone)
        if created:
            logger.info('Создан новый пользователь %s', phone)
        else:
            logger.info('Пользователь %s найден в базе', phone)
        return user

    def _generate_token(self, user):
        """Генерация JWT-токенов (refresh и access)."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
