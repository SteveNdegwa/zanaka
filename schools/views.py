from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from utils.decorators.user_login_required import user_login_required
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider
from .services.school_services import SchoolServices


@user_login_required(required_permission='schools.list_schools')
def list_schools(request: ExtendedRequest) -> JsonResponse:
    schools = SchoolServices.filter_schools(**request.data)
    return ResponseProvider.success(
        message='Schools fetched successfully',
        data=schools
    )


@user_login_required(required_permission='schools.create_school')
def create_school(request: ExtendedRequest) -> JsonResponse:
    school = SchoolServices.create_school(**request.data)
    return ResponseProvider.created(
        message='School created successfully',
        data={'id': str(school.id)}
    )


@user_login_required(required_permission='schools.view_school')
def view_school(request: ExtendedRequest, school_id: str) -> JsonResponse:
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    school = SchoolServices.get_school_profile(school_id)

    return ResponseProvider.success(
        message='School fetched successfully',
        data=school
    )


@user_login_required(required_permission='schools.update_school')
def update_school(request: ExtendedRequest, school_id: str) -> JsonResponse:
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    SchoolServices.update_school(school_id, **request.data)

    return ResponseProvider.success(
        message='School updated successfully'
    )


@user_login_required(required_permission='schools.delete_school')
def delete_school(request: ExtendedRequest, school_id: str) -> JsonResponse:
    if school_id != request.user.branch.school.id:
        raise PermissionDenied()

    SchoolServices.delete_school(school_id)

    return ResponseProvider.success(
        message='School deleted successfully'
    )


@user_login_required(required_permission='schools.list_branches')
def list_branches(request: ExtendedRequest) -> JsonResponse:
    school_id = request.user.school.id
    branches = SchoolServices.filter_branches(school_id, **request.data)

    return ResponseProvider.success(
        message='Branches fetched successfully',
        data=branches
    )


@user_login_required(required_permission='schools.create_branch')
def create_branch(request: ExtendedRequest) -> JsonResponse:
    branch = SchoolServices.create_branch(request.user.school, **request.data)

    return ResponseProvider.created(
        message='Branch created successfully',
        data={'id': str(branch.id)}
    )


@user_login_required(required_permission='schools.view_branch')
def view_branch(request: ExtendedRequest, branch_id: str) -> JsonResponse:
    # if branch_id != request.user.school.id:
    #     raise PermissionDenied()

    branch = SchoolServices.get_branch_profile(branch_id)

    return ResponseProvider.success(
        message='Branch fetched successfully',
        data=branch
    )


@user_login_required(required_permission='schools.update_branch')
def update_branch(request: ExtendedRequest, branch_id: str) -> JsonResponse:

    SchoolServices.update_branch(request.user, branch_id, **request.data)

    return ResponseProvider.success(
        message='Branch updated successfully'
    )


@user_login_required(required_permission='schools.delete_branch')
def delete_branch(request: ExtendedRequest, branch_id: str) -> JsonResponse:
    # if branch_id != request.user.branch.id:
    #     raise PermissionDenied()

    SchoolServices.delete_branch(branch_id)

    return ResponseProvider.success(
        message='Branch deleted successfully'
    )


@user_login_required(required_permission='schools.list_classrooms')
def list_classrooms(request: ExtendedRequest) -> JsonResponse:
    classrooms = SchoolServices.filter_classrooms(request.user.school.id, **request.data)

    return ResponseProvider.success(
        message='Classrooms fetched successfully',
        data=classrooms
    )


@user_login_required(required_permission='schools.create_classroom')
def create_classroom(request: ExtendedRequest) -> JsonResponse:

    classroom = SchoolServices.create_classroom(**request.data)

    return ResponseProvider.created(
        message='Classroom created successfully',
        data={'id': str(classroom.id)}
    )


@user_login_required(required_permission='schools.view_classroom')
def view_classroom(request: ExtendedRequest, classroom_id: str) -> JsonResponse:
    classroom = SchoolServices.get_classroom(classroom_id)
    # if classroom.branch.id != request.user.branch.id:
    #     raise PermissionDenied()

    classroom = SchoolServices.get_classroom_profile(classroom_id)

    return ResponseProvider.success(
        message='Classroom fetched successfully',
        data=classroom
    )


@user_login_required(required_permission='schools.update_classroom')
def update_classroom(request: ExtendedRequest, classroom_id: str) -> JsonResponse:
    # classroom = SchoolServices.get_classroom(classroom_id)
    # if classroom.branch.id != request.user.branch.id:
    #     raise PermissionDenied()

    SchoolServices.update_classroom(classroom_id, **request.data)

    return ResponseProvider.success(
        message='Classroom updated successfully'
    )


@user_login_required(required_permission='schools.delete_classroom')
def delete_classroom(request: ExtendedRequest, classroom_id: str) -> JsonResponse:
    # classroom = SchoolServices.get_classroom(classroom_id)
    # if classroom.branch.id != request.user.branch.id:
    #     raise PermissionDenied()

    SchoolServices.delete_classroom(classroom_id)

    return ResponseProvider.success(
        message='Classroom deleted successfully'
    )
