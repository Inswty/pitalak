import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

AUTH_USER_MODEL = 'users.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'phonenumber_field',
    'rest_framework',
    'djoser',
    'django_db_logger',
    'nested_admin',
    'api.apps.ApiConfig',
    'core.apps.CoreConfig',
    'orders.apps.OrdersConfig',
    'products.apps.ProductsConfig',
    'users.apps.UsersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pitalak_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pitalak_backend.wsgi.application'

# OTP settings
SMS_PROVIDER_LOGIN = os.getenv('SMS_PROVIDER_LOGIN')
SMS_PROVIDER_PASSWORD = os.getenv('SMS_PROVIDER_PASSWORD')
SMS_PROVIDER_SENDER = os.getenv('SMS_PROVIDER_SENDER')
SMS_PROVIDER_API_URL = os.getenv('SMS_PROVIDER_API_URL')

OTP_LENGTH = 4
OTP_TTL_SECONDS = 300  # 5 минут
MAX_OTP_ATTEMPTS = 3
MAX_OTP_REQUESTS_PER_HOUR = int(os.getenv("MAX_OTP_REQUESTS_PER_HOUR", 3))
OTP_COOLDOWN_SECONDS = 60  # 1 минута между запросами
OTP_TEXT = 'Ваш код подтверждения: {otp}'

# Cache settings for OTP
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

DJOSER = {
    'USER_CREATE_PASSWORD_RETYPE': False,
    'SEND_ACTIVATION_EMAIL': False,
    'LOGIN_FIELD': 'phone',
}

# Internationalization
LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'Asia/Yekaterinburg'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'collected_static'

# источник статики для dev
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = 'media/'
MEDIA_ROOT = Path('media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Настройки логирования
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': os.path.join(BASE_DIR, 'logs', 'main.log'),
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
        },
        'formatters': {
            'verbose': {
                'format': '[{asctime}] {levelname} {name}: {message}',
                'style': '{',
                'datefmt': '%d-%m-%Y %H:%M:%S',
            },
        },
        'root': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    }
else:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'handlers': {
            'db': {
                'level': 'INFO',
                'class': 'django_db_logger.db_log_handler.DatabaseLogHandler',
            },
        },
        'root': {
            'handlers': ['db'],
            'level': 'INFO',
        },
    }
