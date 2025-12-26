from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet, LoggedTokenRefreshView, OTPViewSet, ProductViewSet,
    UserViewSet
)

v1_router = DefaultRouter()
v1_router.register(r'otp', OTPViewSet, basename='otp')
v1_router.register(r'users', UserViewSet, basename='users')
v1_router.register(r'products', ProductViewSet, basename='products')
v1_router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path(
        'v1/token/refresh/',
        LoggedTokenRefreshView.as_view(),
        name='token_refresh'
    ),
]
