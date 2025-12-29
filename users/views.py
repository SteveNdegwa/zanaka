from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from utils.decorators.user_login_required import user_login_required
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider
from .services.user_services import UserServices


@user_login_required
def create_user(request: ExtendedRequest, role_name: str) -> JsonResponse:
    role_name = role_name.lower()
    # perm = f'users.create_{role_name.lower()}'
    # if not request.user.has_permission(perm):
    #     raise PermissionDenied()

    user = UserServices.create_user(request.user, role_name, **request.data)

    return ResponseProvider.created(
        message=f'{role_name.title()} created successfully',
        data={'id': str(user.id)}
    )


@user_login_required
def update_user(request: ExtendedRequest, user_id: str) -> JsonResponse:
    # if user_id != request.user.id:
    #     user_to_update = UserServices.get_user(user_id)
    #     perm = f'users.update_{user_to_update.role.name}'
    #     if not request.user.has_permission(perm):
    #         raise PermissionDenied()

    UserServices.update_user(request.user, user_id, **request.data)

    return ResponseProvider.success(
        message='User updated successfully'
    )


@user_login_required
def delete_user(request: ExtendedRequest, user_id: str) -> JsonResponse:
    # if user_id != request.user.id:
    #     user_to_update = UserServices.get_user(user_id)
    #     perm = f'users.delete_{user_to_update.role.name}'
    #     if not request.user.has_permission(perm):
    #         raise PermissionDenied()

    UserServices.delete_user(user_id)

    return ResponseProvider.success(
        message='User deleted successfully'
    )


@user_login_required
def view_user(request: ExtendedRequest, user_id: str) -> JsonResponse:
    user_profile = UserServices.get_user_profile(user_id)
    # if user_id != request.user.id:
    #     perm = f'users.view_{user_profile.get('role_name')}'
    #     if not request.user.has_permission(perm):
    #         raise PermissionDenied()

    return ResponseProvider.success(
        message='User data fetched successfully',
        data=user_profile
    )

@user_login_required
def list_users(request: ExtendedRequest) -> JsonResponse:
    # if not request.user.has_permission('users.list_all_users'):
    #     if not 'role_name' in request.data:
    #         raise PermissionDenied()
    #     perm = f'users.list_{request.data.get('role_name')}s'
    #     if not request.user.has_permission(perm):
    #         raise PermissionDenied()

    users = UserServices.filter_users(request.user, **request.data)

    return ResponseProvider.success(
        message='Users fetched successfully',
        data=users
    )


def forgot_password(request: ExtendedRequest) -> JsonResponse:
    credential = request.data.get('credential')
    UserServices.forgot_password(credential)
    return ResponseProvider.success(
        message='Password reset successfully'
    )


@user_login_required(required_permission='users.reset_password')
def reset_password(request: ExtendedRequest, user_id: str) -> JsonResponse:
    UserServices.reset_password(user_id)
    return ResponseProvider.success(
        message='Password reset successfully'
    )


@user_login_required
def change_password(request: ExtendedRequest) -> JsonResponse:
    user_id = request.user.id
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    UserServices.change_password(
        user_id=user_id,
        current_password=current_password,
        new_password=new_password,
    )

    return ResponseProvider.success(
        message='Password changed successfully'
    )


@user_login_required(required_permission='users.add_guardian')
def add_guardian(request: ExtendedRequest, student_id: str) -> JsonResponse:
    student_guardian = UserServices.add_guardian_to_student(
        student_id=student_id,
        **request.data
    )
    return ResponseProvider.created(
        message='Guardian added successfully',
        data={'id': student_guardian.id}
    )


@user_login_required(required_permission='users.remove_guardian')
def remove_guardian(request: ExtendedRequest, student_id: str, guardian_id: str) -> JsonResponse:
    UserServices.remove_guardian_from_student(
        student_id=student_id,
        guardian_id=guardian_id
    )
    return ResponseProvider.success(
        message='Guardian removed successfully'
    )


@user_login_required(required_permission='users.list_guardians')
def list_guardians(request: ExtendedRequest, student_id: str) -> JsonResponse:
    guardians = UserServices.filter_guardians_for_student(student_id, **request.data)
    return ResponseProvider.success(
        message='Guardians fetched successfully',
        data=guardians
    )
