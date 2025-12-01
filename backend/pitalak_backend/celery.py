import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitalak_backend.settings')

app = Celery('pitalak')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery поищет tasks.py во всех приложениях
app.autodiscover_tasks()
