from django.urls import path

from .views import refresh_sms_balance

app_name = 'admin_extensions'

urlpatterns = [
    path(
        'refresh-sms-balance/', refresh_sms_balance, name='refresh_sms_balance'
    ),
]
