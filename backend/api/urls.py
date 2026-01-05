from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
)
from rest_framework.routers import DefaultRouter

from .views import (
    CartViewSet, CategoryViewSet, LoggedTokenRefreshView, OrderViewSet,
    OTPViewSet, ProductViewSet, UserViewSet
)

app_name = 'api'

v1_router = DefaultRouter()
v1_router.register(r'otp', OTPViewSet, basename='otp')
v1_router.register(r'users', UserViewSet, basename='users')
v1_router.register(r'products', ProductViewSet, basename='products')
v1_router.register(r'categories', CategoryViewSet, basename='categories')
v1_router.register(r'cart', CartViewSet, basename='cart')
v1_router.register(r'orders', OrderViewSet, basename='orders')

docs_urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'swagger/',
        SpectacularSwaggerView.as_view(url_name='api:api-docs:schema'),
        name='swagger-ui'
    ),
    path(
        'redoc/',
        SpectacularRedocView.as_view(url_name='api:api-docs:schema'),
        name='redoc'
    ),
]

urlpatterns = [
    path('v1/', include(v1_router.urls)),
    path(
        'v1/token/refresh/',
        LoggedTokenRefreshView.as_view(),
        name='token_refresh'
    ),
    path('docs/', include((docs_urlpatterns, 'api-docs'))),
]
