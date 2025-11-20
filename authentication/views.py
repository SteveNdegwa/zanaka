from authentication.models import Identity
from authentication.services.auth_services import AuthServices
from users.services.user_services import UserServices
from utils.decorators.user_login_required import user_login_required
from utils.response_provider import ResponseProvider


def login(request):
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
    if identity.status == Identity.Status.ACTIVE:
        user_profile = UserServices.get_user_profile(identity.user.id)

    return ResponseProvider.success(
        message='Login successful',
        data={
            'token': str(identity.token),
            'status': identity.status,
            'user_id': str(identity.user.id),
            'expires_at': str(identity.expires_at),
            'profile': user_profile,
        }
    )


@user_login_required
def logout(request):
    AuthServices.logout(request.user)
    return ResponseProvider.success(message='Logout successful')
