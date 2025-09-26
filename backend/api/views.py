import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

from core.managers.otp_manager import OTPManager
from users.models import User
from .services.sms_provider import TargetSMSClient
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
            logger.error('Ошибка при отправке OTP: %s', e)
            raise ValidationError({'detail': 'Не удалось отправить OTP',
                                  'error': str(e)})

        if not settings.DEBUG:
            message_id = TargetSMSClient().send_sms(phone=phone, otp=otp)
        else:
            print(f'DEV MODE: OTP на номер {phone}: {otp}')
            message_id = 'dev_mode'

        status_msg = 'OTP отправлен на номер: {}'.format(phone)
        if message_id or settings.DEBUG:
            logger.info('OTP "%s" отправлен на %s', otp, phone)
            return Response({
                'detail': status_msg,
                'TTL': settings.OTP_TTL_SECONDS
            }, status=status.HTTP_200_OK)
        return Response({'detail': 'Ошибка при отправке OTP.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
