from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

from core.constants import MAX_STR_LENGTH


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Номер телефона должен быть добавлен')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя."""

    # Убираем username
    username = None

    phone = models.CharField(
        'Номер телефона',
        max_length=15,
        unique=True
    )
    phone_verified = models.BooleanField(
        'Телефон подтвержден',
        default=False
    )
    email = models.EmailField(
        'Email',
        blank=True,
        null=True
    )
    name = models.CharField(
        'Имя',
        max_length=150,
        blank=True,
        null=True
    )

    # Используем phone как поле для входа
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []  # Убираем обязательные поля

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('phone',)

    def __str__(self):
        return f'{self.phone} ♦ {self.name or ""}'[:MAX_STR_LENGTH]
