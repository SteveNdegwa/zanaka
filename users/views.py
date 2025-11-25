from django.core.exceptions import PermissionDenied

from utils.decorators.user_login_required import user_login_required
from utils.response_provider import ResponseProvider
from .services.user_services import UserServices


@user_login_required
def create_user(request, role_name):
    perm = f"can_create_{role_name.lower()}"
    if not request.user.has_permission(perm):
        raise PermissionDenied()

    request.data["branch_id"] = request.user.branch.id
    user = UserServices.create_user(role_name, **request.data)

    return ResponseProvider.created(
        message=f"{role_name.title()} created successfully",
        data={"id": str(user.id)}
    )


@user_login_required
def update_user(request, user_id):
    if user_id != request.user.id:
        user_to_update = UserServices.get_user(user_id)
        perm = f"can_update_{user_to_update.role.name}"
        if not request.user.has_permission(perm):
            raise PermissionDenied()

    UserServices.update_user(user_id, **request.data)

    return ResponseProvider.success(
        message="User updated successfully"
    )


@user_login_required
def delete_user(request, user_id):
    if user_id != request.user.id:
        user_to_update = UserServices.get_user(user_id)
        perm = f"can_delete_{user_to_update.role.name}"
        if not request.user.has_permission(perm):
            raise PermissionDenied()

    UserServices.delete_user(user_id)

    return ResponseProvider.success(
        message="User deleted successfully"
    )


@user_login_required
def view_user(request, user_id):
    user_profile = UserServices.get_user_profile(user_id)
    if user_id != request.user.id:
        perm = f"can_view_{user_profile.get("role_name")}"
        if not request.user.has_permission(perm):
            raise PermissionDenied()

    return ResponseProvider.success(
        message="User data fetched successfully",
        data=user_profile
    )

@user_login_required
def list_users(request):
    if not request.user.has_permission("can_list_all_users"):
        if not "role_name" in request.data:
            raise PermissionDenied()
        perm = f"can_list_{request.data.get("role_name")}s"
        if not request.user.has_permission(perm):
            raise PermissionDenied()

    request.data.set_default("branch_id", request.user.branch.id)
    users = UserServices.filter_users(**request.data)

    return ResponseProvider.success(
        message="Users fetched successfully",
        data=users
    )


def forgot_password(request):
    credential = request.data.get("credential")
    UserServices.forgot_password(credential)
    return ResponseProvider.success(
        message="Password reset successfully"
    )


@user_login_required(required_permission="can_reset_password")
def reset_password(request, user_id):
    UserServices.reset_password(user_id)
    return ResponseProvider.success(
        message="Password reset successfully"
    )


@user_login_required
def change_password(request):
    user_id = request.user.id
    new_password = request.data.get("new_password")
    old_password = request.data.get("old_password")

    UserServices.change_password(
        user_id=user_id,
        new_password=new_password,
        old_password=old_password
    )

    return ResponseProvider.success(
        message="Password changed successfully"
    )


@user_login_required(required_permission="can_add_guardian")
def add_guardian(request, student_id):
    guardian = UserServices.add_guardian_to_student(student_id=student_id, **request.data)
    return ResponseProvider.created(
        message="Guardian added successfully",
        data={"id": str(guardian.id)}
    )


@user_login_required(required_permission="can_remove_guardian")
def remove_guardian(request, student_id, guardian_id):
    UserServices.remove_guardian_from_student(
        student_id=student_id,
        guardian_id=guardian_id
    )
    return ResponseProvider.success(
        message="Guardian removed successfully"
    )


@user_login_required(required_permission="can_list_guardians")
def list_guardians(request, student_id):
    guardians = UserServices.filter_guardians_for_student(student_id, **request.data)
    return ResponseProvider.success(
        message="Guardians fetched successfully",
        data=guardians
    )
