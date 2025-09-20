import logging

from audit.decorators import set_activity_name
from authentication.decorators import user_login_required
from base.views import BaseView
from users.services.user_service import UserService
from utils.response_provider import ResponseProvider

logger = logging.getLogger(__name__)


class UserView(BaseView):
    @user_login_required
    @set_activity_name('Fetch User(s)')
    def get(self, request, user_id=None, *args, **kwargs):
        if user_id:
            user_data = UserService.get_user_profile(user_id)
            return ResponseProvider.success(
                message='User fetched successfully',
                data=user_data
            )
        users_data = UserService.filter_users(**self.data)
        return ResponseProvider.success(
            message='Users filtered successfully',
            data=users_data
        )

    @user_login_required
    @set_activity_name('Create User')
    def post(self, request, role_name, *args, **kwargs):
        user = UserService.create_user(role_name, **self.data)
        return ResponseProvider.created(
            message='User created successfully',
            data={'user_id': str(user.id)}
        )

    @user_login_required
    @set_activity_name('Update User')
    def put(self, request, user_id, *args, **kwargs):
        UserService.update_user(user_id, **self.data)
        return ResponseProvider.success(message='User updated successfully')

    @user_login_required
    @set_activity_name('Delete User')
    def delete(self, request, user_id, *args, **kwargs):
        UserService.delete_user(user_id)
        return ResponseProvider.success(message='User deleted successfully')
