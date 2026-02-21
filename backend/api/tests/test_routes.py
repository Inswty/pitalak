import pytest
from django.urls import reverse
from rest_framework import status

USER_CLIENT = 'client'
AUTH_CLIENT = 'auth_client'

PERMISSIONS_DATA = (
    # Публичные эндпоинты
    (USER_CLIENT, 'api:categories-list', status.HTTP_200_OK),
    (AUTH_CLIENT, 'api:categories-list', status.HTTP_200_OK),

    (USER_CLIENT, 'api:products-list', status.HTTP_200_OK),
    (AUTH_CLIENT, 'api:products-list', status.HTTP_200_OK),

    # Приватные эндпойнты
    (USER_CLIENT, 'api:users-me', status.HTTP_401_UNAUTHORIZED),
    (AUTH_CLIENT, 'api:users-me', status.HTTP_200_OK),

    (USER_CLIENT, 'api:addresses-list', status.HTTP_401_UNAUTHORIZED),
    (AUTH_CLIENT, 'api:addresses-list', status.HTTP_200_OK),

    (USER_CLIENT, 'api:cart-me', status.HTTP_401_UNAUTHORIZED),
    (AUTH_CLIENT, 'api:cart-me', status.HTTP_200_OK),

    (USER_CLIENT, 'api:orders-list', status.HTTP_401_UNAUTHORIZED),
    (AUTH_CLIENT, 'api:orders-list', status.HTTP_200_OK),

    (USER_CLIENT, 'api:checkout-list', status.HTTP_401_UNAUTHORIZED),
    (AUTH_CLIENT, 'api:checkout-list', status.HTTP_200_OK),

    pytest.param(
        USER_CLIENT, 'api:api-docs:swagger-ui',
        status.HTTP_401_UNAUTHORIZED,
        marks=pytest.mark.xfail(reason='Временно доступно всем')
    ),
    (AUTH_CLIENT, 'api:api-docs:swagger-ui', status.HTTP_200_OK),

    pytest.param(
        USER_CLIENT, 'api:api-docs:redoc',
        status.HTTP_401_UNAUTHORIZED,
        marks=pytest.mark.xfail(reason='Временно доступно всем')
    ),
    (AUTH_CLIENT, 'api:api-docs:redoc', status.HTTP_200_OK),

    pytest.param(
        USER_CLIENT, 'api:api-docs:schema',
        status.HTTP_401_UNAUTHORIZED,
        marks=pytest.mark.xfail(reason='Временно доступно всем')
    ),
    (AUTH_CLIENT, 'api:api-docs:schema', status.HTTP_200_OK),

    # Специфические (OTP только POST, поэтому GET везде 405)
    (USER_CLIENT, 'api:otp-send', status.HTTP_405_METHOD_NOT_ALLOWED),
    (AUTH_CLIENT, 'api:otp-send', status.HTTP_405_METHOD_NOT_ALLOWED),

    (USER_CLIENT, 'api:otp-verify', status.HTTP_405_METHOD_NOT_ALLOWED),
    (AUTH_CLIENT, 'api:otp-verify', status.HTTP_405_METHOD_NOT_ALLOWED),
)


@pytest.mark.django_db
@pytest.mark.parametrize('client_name, url_name, expected_status',
                         PERMISSIONS_DATA)
def test_api_routes_permissions(client_name, url_name, expected_status,
                                request):
    """
    Комплексная проверка прав доступа (Аноним vs Авторизованный).
    """

    client = request.getfixturevalue(client_name)
    url = reverse(url_name)

    assert client.get(url).status_code == expected_status
