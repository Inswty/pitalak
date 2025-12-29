from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField

from core.constants import MAX_STR_LENGTH


class UserManager(BaseUserManager):
    """Менеджер пользователей с номером телефона вместо username."""

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

    phone = PhoneNumberField('Номер телефона', unique=True, region='RU')
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


class Address(models.Model):
    """Адреса пользователей."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='Пользователь'
    )
    locality = models.CharField(
        'Населённый пункт', default='Тюмень', max_length=255
    )
    street = models.CharField('Улица', max_length=255)
    house = models.CharField('Дом', max_length=20)
    flat = models.CharField('Квартира', max_length=10, blank=True, null=True)
    floor = models.CharField('Этаж', max_length=10, blank=True, null=True)
    added = models.DateTimeField('Добавлен', auto_now_add=True)

    is_primary = models.BooleanField("Основной", default=False)

    def save(self, *args, **kwargs):
        # Если ещё нет адресов — этот будет основным
        if not Address.objects.filter(user=self.user).exists():
            self.is_primary = True
        # Если этот адрес отмечается как основной — сбрасываем у остальных
        if self.is_primary:
            Address.objects.filter(
                user=self.user, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def format_address_display(self):
        """Вспомогательный метод для форматирования адреса."""
        parts = filter(None, [
            self.locality,
            f'ул. {self.street}',
            f'д. {self.house}' if self.house else None,
            f'кв. {self.flat}' if self.flat else None,
            f'эт. {self.floor}' if self.floor else None,
        ])
        return ', '.join(parts)

    class Meta:
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'
        ordering = ('id',)

    def __str__(self):
        """Отображение адреса в админке."""
        display_text = self.format_address_display()
        # Добавим ⭐, если адрес основной
        if self.is_primary:
            return f'{display_text}  [⭐]'
        return display_text
