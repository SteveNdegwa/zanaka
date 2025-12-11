from django.http import JsonResponse

from authentication.models import IdentityStatus
from authentication.services.auth_services import AuthServices
from base.services.system_settings_cache import SystemSettingsCache
from users.services.user_services import UserServices
from utils.decorators.user_login_required import user_login_required
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider


def login(request: ExtendedRequest) -> JsonResponse:
    credential = request.data.get('credential', '')
    password = request.data.get('password', '')
    device_token = request.data.get('device_token', '')
    source_ip = getattr(request, 'ip_address', None)

    identity = AuthServices.login(
        credential=credential,
        password=password,
        source_ip=source_ip,
        device_token=device_token,
    )

    user_profile = None
    if identity.status == IdentityStatus.ACTIVE:
        user_profile = UserServices.get_user_profile(identity.user.id)

    data = {
        'identity_status': identity.status,
        'user_profile': user_profile,
    }
    response = ResponseProvider.success(message='Login successful', data=data)

    system_settings = SystemSettingsCache.get()
    response.set_cookie(
        key=system_settings.auth_token_cookie_name,
        value=str(identity.token),
        httponly=True,
        secure=system_settings.cookie_secure,
        samesite='Strict',
        max_age=3600,
        path='/'
    )

    return response


@user_login_required
def logout(request: ExtendedRequest) -> JsonResponse:
    AuthServices.logout(request.user)
    response = ResponseProvider.success(message='Logout successful')
    response.delete_cookie(SystemSettingsCache.get().auth_token_cookie_name, path='/')
    return response