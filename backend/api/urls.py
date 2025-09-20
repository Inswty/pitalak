from django.urls import path
from rest_framework.routers import DefaultRouter

from api.views import SendOTPAPIView, VerifyOTPAPIView

v1_router = DefaultRouter()
# v1_router.register()

urlpatterns = [
    path('v1/otp/send/', SendOTPAPIView.as_view(), name='send-otp'),
    path('v1/otp/verify/', VerifyOTPAPIView.as_view(), name='verify-otp'),
]
