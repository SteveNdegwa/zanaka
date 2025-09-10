import logging

from audit.context import RequestContext
from authentication.backend.authentication_management_service import AuthenticationManagementService
from utils.response_provider import ResponseProvider

logger = logging.getLogger(__name__)


class AuthenticationAPIHandler:
    @staticmethod
    def login(request):
        """
        Authenticates a user based on provided credentials and returns an active identity token.

        :param request: HTTP request object.
        :type request: HttpRequest
        :return: JSON response containing token, status, user ID, expiration time, and optional user profile.
        :rtype: JsonResponse
        :raises Exception: If authentication fails or an error occurs during login.
        """
        try:
            data = RequestContext.data
            credential = data.get('credential', '')
            password = data.get('password', '')
            device_token = data.get('device_token', '')
            source_ip = RequestContext.ip_address

            identity = AuthenticationManagementService().login(
                credential=credential,
                password=password,
                source_ip=source_ip,
                device_token=device_token
            )

            user_profile = None
            # if identity.status == Identity.Status.ACTIVE:
            #     user_profile = UserManagementService().get_user(user_id=identity.user.id)

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
        except Exception as ex:
            logger.exception('AuthenticationAPIHandler - login exception: %s', ex)
            return ResponseProvider.error(message='An error occurred during login', error=str(ex))

    @staticmethod
    def logout(request):
        """
        Logs out a user from a specific system by invalidating their active identity.

        :param request: HTTP request object.
        :type request: HttpRequest
        :return: JSON response indicating whether the logout was successful.
        :rtype: JsonResponse
        :raises Exception: If logout fails or the identity cannot be terminated.
        """
        try:
            user_id = RequestContext.data.get('user_id', '')
            AuthenticationManagementService().logout(user_id=user_id)
            return ResponseProvider.success(message='Logout successful')
        except Exception as ex:
            logger.exception('AuthenticationAPIHandler - logout exception: %s', ex)
            return ResponseProvider.error(message='An error occurred during logout', error=str(ex))
