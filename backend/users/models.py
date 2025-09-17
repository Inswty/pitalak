from django.db import models
from django.contrib.auth.models import AbstractUser

from core.constants import MAX_STR_LENGTH


class User(AbstractUser):
    """Кастомная модель пользователя."""

    phone = models.CharField('Номер телефона', max_length=15, unique=True)
    phone_verified = models.BooleanField('Телефон подтвержден', default=False)   # ?
    # Делаем username необязательным
    username = models.CharField(
        max_length=150,   #  ?
        unique=True,
        blank=True,
        null=True,
        editable=False  # Скрываем из админки и форм   ?
    )

    # Используем phone как поле для входа
    USERNAME_FIELD = 'phone'
    # REQUIRED_FIELDS = ('first_name',)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)   # ?

    def __str__(self):
        return f'{self.phone} ({self.username()})'[:MAX_STR_LENGTH]
