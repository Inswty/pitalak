from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, SendOTPAPIView, VerifyOTPAPIView

v1_router = DefaultRouter()
v1_router.register(r'products', ProductViewSet, basename='products')

urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path('v1/otp/send/', SendOTPAPIView.as_view(), name='send-otp'),
    path('v1/otp/verify/', VerifyOTPAPIView.as_view(), name='verify-otp'),
]
