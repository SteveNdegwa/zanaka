import logging

from audit.context import RequestContext
from audit.decorators import set_activity_name
from authentication.models import Identity
from authentication.services.auth_service import AuthService
from base.views import BaseView
from users.services.user_service import UserService
from utils.response_provider import ResponseProvider

logger = logging.getLogger(__name__)

class AuthView(BaseView):
    def post(self, request, action, *args, **kwargs):
        if action == "login":
            return self.login(request, *args, **kwargs)
        elif action == "logout":
            return self.logout(request, *args, **kwargs)
        else:
            return ResponseProvider.bad_request(message="Invalid action specified")

    @set_activity_name("User login")
    def login(self, request, *args, **kwargs):
        reg_number = self.data.get('reg_number', '')
        password = self.data.get('password', '')
        device_token = self.data.get('device_token', '')
        source_ip = RequestContext.ip_address

        identity = AuthService.login(
            reg_number=reg_number,
            password=password,
            source_ip=source_ip,
            device_token=device_token,
        )

        user_profile = None
        if identity.status == Identity.Status.ACTIVE:
            user_profile = UserService.get_user_profile(identity.user.id)

        return ResponseProvider.success(
            message="Login successful",
            data={
                "token": str(identity.token),
                "status": identity.status,
                "user_id": str(identity.user.id),
                "expires_at": str(identity.expires_at),
                "profile": user_profile,
            }
        )

    @set_activity_name("User logout")
    def logout(self, request, *args, **kwargs):
        user_id = self.data.get("user_id", "")
        AuthService.logout(user_id)
        return ResponseProvider.success(message="Logout successful")
