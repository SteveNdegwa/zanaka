from django.core.exceptions import PermissionDenied

from utils.decorators.user_login_required import user_login_required
from utils.response_provider import ResponseProvider
from .services.school_services import SchoolServices


@user_login_required(required_permission="schools.list_schools")
def list_schools(request):
    schools = SchoolServices.filter_schools(**request.data)
    return ResponseProvider.success(
        message="Schools fetched successfully",
        data=schools
    )


@user_login_required(required_permission="schools.create_school")
def create_school(request):
    school = SchoolServices.create_school(**request.data)
    return ResponseProvider.created(
        message="School created successfully",
        data={"id": str(school.id)}
    )


@user_login_required(required_permission="schools.view_school")
def view_school(request, school_id):
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    school = SchoolServices.get_school_profile(school_id)

    return ResponseProvider.success(
        message="School fetched successfully",
        data=school
    )


@user_login_required(required_permission="schools.update_school")
def update_school(request, school_id):
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    SchoolServices.update_school(school_id, **request.data)

    return ResponseProvider.success(
        message="School updated successfully"
    )


@user_login_required(required_permission="schools.delete_school")
def delete_school(request, school_id):
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    SchoolServices.delete_school(school_id)

    return ResponseProvider.success(
        message="School deleted successfully"
    )


@user_login_required(required_permission="schools.list_branches")
def list_branches(request, school_id):
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    branches = SchoolServices.filter_branches(school_id, **request.data)

    return ResponseProvider.success(
        message="Branches fetched successfully",
        data=branches
    )


@user_login_required(required_permission="schools.create_branch")
def create_branch(request, school_id):
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    branch = SchoolServices.create_branch(school_id, **request.data)

    return ResponseProvider.created(
        message="Branch created successfully",
        data={"id": str(branch.id)}
    )


@user_login_required(required_permission="schools.view_branch")
def view_branch(request, branch_id):
    if branch_id != request.user.branch.id:
        raise PermissionDenied()

    branch = SchoolServices.get_branch_profile(branch_id)

    return ResponseProvider.success(
        message="Branch fetched successfully",
        data=branch
    )


@user_login_required(required_permission="schools.update_branch")
def update_branch(request, branch_id):
    if branch_id != request.user.branch.id:
        raise PermissionDenied()

    SchoolServices.update_branch(branch_id, **request.data)

    return ResponseProvider.success(
        message="Branch updated successfully"
    )


@user_login_required(required_permission="schools.delete_branch")
def delete_branch(request, branch_id):
    if branch_id != request.user.branch.id:
        raise PermissionDenied()

    SchoolServices.delete_branch(branch_id)

    return ResponseProvider.success(
        message="Branch deleted successfully"
    )


@user_login_required(required_permission="schools.list_classrooms")
def list_classrooms(request, branch_id):
    if branch_id != request.user.branch.id:
        raise PermissionDenied()

    classrooms = SchoolServices.filter_classrooms(branch_id, **request.data)

    return ResponseProvider.success(
        message="Classrooms fetched successfully",
        data=classrooms
    )


@user_login_required(required_permission="schools.create_classroom")
def create_classroom(request, branch_id):
    if branch_id != request.user.branch.id:
        raise PermissionDenied()

    classroom = SchoolServices.create_classroom(branch_id, **request.data)

    return ResponseProvider.created(
        message="Classroom created successfully",
        data={"id": str(classroom.id)}
    )


@user_login_required(required_permission="schools.view_classroom")
def view_classroom(request, classroom_id):
    classroom = SchoolServices.get_classroom(classroom_id)
    if classroom.branch.id != request.user.branch.id:
        raise PermissionDenied()

    classroom = SchoolServices.get_classroom_profile(classroom_id)

    return ResponseProvider.success(
        message="Classroom fetched successfully",
        data=classroom
    )


@user_login_required(required_permission="schools.update_classroom")
def update_classroom(request, classroom_id):
    classroom = SchoolServices.get_classroom(classroom_id)
    if classroom.branch.id != request.user.branch.id:
        raise PermissionDenied()

    SchoolServices.update_classroom(classroom_id, **request.data)

    return ResponseProvider.success(
        message="Classroom updated successfully"
    )


@user_login_required(required_permission="schools.delete_classroom")
def delete_classroom(request, classroom_id):
    classroom = SchoolServices.get_classroom(classroom_id)
    if classroom.branch.id != request.user.branch.id:
        raise PermissionDenied()

    SchoolServices.delete_classroom(classroom_id)

    return ResponseProvider.success(
        message="Classroom deleted successfully"
    )
