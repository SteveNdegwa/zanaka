from typing import Optional

from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q

from base.services.base_services import BaseServices
from schools.models import School, Branch, Classroom


class SchoolServices(BaseServices):
    """
    Service layer for managing schools, branches, and classrooms.
    """

    fk_mappings = {
        'school_id': ('schools.School', 'school'),
        'branch_id': ('schools.Branch', 'branch'),
        'classroom_id': ('schools.Classroom', 'classroom'),
        'principal_id': ('users.User', 'principal'),
    }

    @classmethod
    def get_school(cls, school_id: str, select_for_update: bool = False) -> School:
        """
        Retrieve a school by ID.

        :param school_id: ID of the school.
        :param select_for_update: Whether to apply row-level locking.
        :raises ValidationError: If the school does not exist or is inactive.
        :rtype: School
        """
        qs = School.objects
        if select_for_update:
            qs = qs.select_for_update()
        try:
            return qs.get(id=school_id, is_active=True)
        except School.DoesNotExist:
            raise ObjectDoesNotExist('School not found')

    @classmethod
    @transaction.atomic
    def create_school(cls, **data) -> School:
        """
        Create a new school.

        :param data: Data for the new school.
        :raises ValidationError: If required fields are missing or code already exists.
        :rtype: School
        """
        required_fields = {'name', 'code'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)
        data['code'] = str(data['code']).upper().strip()
        if len(data['code']) < 3:
            raise ValidationError('Code must be at least 3 characters long')
        if len(data['code']) > 10:
            raise ValidationError('Code must not exceed 10 characters')
        if School.objects.filter(code=data.get('code')).exists():
            raise ValidationError('Code already exists')
        return School.objects.create(**data)

    @classmethod
    @transaction.atomic
    def update_school(cls, school_id: str, **data) -> School:
        """
        Update an existing school.

        :param school_id: ID of the school.
        :param data: Fields to update.
        :raises ValidationError: If school does not exist or data is invalid.
        :rtype: School
        """
        school = cls.get_school(school_id, True)
        allowed_fields = {'address', 'contact_email', 'contact_phone', 'established_date'}
        data = cls._sanitize_and_validate_data(data, allowed_fields=allowed_fields)
        for k, v in data.items():
            setattr(school, k, v)
        school.save()
        return school

    @classmethod
    @transaction.atomic
    def delete_school(cls, school_id: str) -> None:
        """
        Soft-delete a school by marking it inactive.

        :param school_id: ID of the school.
        :raises ValidationError: If school does not exist.
        :rtype: None
        """
        school = cls.get_school(school_id, True)
        school.is_active = False
        school.save(update_fields=['is_active'])

    @classmethod
    def get_school_profile(cls, school_id: str) -> dict:
        """
        Get profile details of a school.

        :param school_id: ID of the school.
        :raises ValidationError: If school does not exist.
        :rtype: dict
        """
        school = cls.get_school(school_id)
        return {
            'id': school.id,
            'name': school.name,
            'code': school.code,
            'address': school.address,
            'contact_email': school.contact_email,
            'contact_phone': school.contact_phone,
            'established_date': school.established_date,
            'is_active': school.is_active,
        }

    @classmethod
    def filter_schools(cls, **filters) -> list[dict]:
        """
        Filter and return profiles of active schools.

        :param filters: Filters for the query.
        :rtype: list[dict]
        """
        qs = School.objects.filter(is_active=True, **filters)
        return [cls.get_school_profile(s.id) for s in qs]

    @classmethod
    def get_branch(cls, branch_id: str, select_for_update: bool = False) -> Branch:
        """
        Retrieve a branch by ID.

        :param branch_id: ID of the branch.
        :param select_for_update: Whether to apply row-level locking.
        :raises ValidationError: If branch does not exist or is inactive.
        :rtype: Branch
        """
        qs = Branch.objects.select_related('school', 'principal')
        if select_for_update:
            qs = qs.select_for_update()
        try:
            return qs.get(id=branch_id, is_active=True)
        except Branch.DoesNotExist:
            raise ObjectDoesNotExist('Branch not found')

    @classmethod
    @transaction.atomic
    def create_branch(cls, school_id: str, **data) -> Branch:
        """
        Create a new branch under a school.

        :param school_id: ID of the school.
        :param data: Data for the new branch.
        :raises ValidationError: If required fields are missing or branch already exists.
        :rtype: Branch
        """
        school = cls.get_school(school_id)
        required_fields = {'name'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)
        if Branch.objects.filter(school=school, name=data.get('name')):
            raise ValidationError('Branch already exists')
        return Branch.objects.create(school=school, **data)

    @classmethod
    @transaction.atomic
    def update_branch(cls, branch_id: str, **data) -> Branch:
        """
        Update an existing branch.

        :param branch_id: ID of the branch.
        :param data: Fields to update.
        :raises ValidationError: If branch does not exist or data is invalid.
        :rtype: Branch
        """
        branch = cls.get_branch(branch_id, True)
        allowed_fields = {
            'location',
            'contact_email',
            'contact_phone',
            'principal_id',
            'capacity',
            'established_date',
        }
        data = cls._sanitize_and_validate_data(data, allowed_fields=allowed_fields)
        for k, v in data.items():
            setattr(branch, k, v)
        branch.save()
        return branch

    @classmethod
    @transaction.atomic
    def delete_branch(cls, branch_id: str) -> None:
        """
        Soft-delete a branch by marking it inactive.

        :param branch_id: ID of the branch.
        :raises ValidationError: If branch does not exist.
        :rtype: None
        """
        branch = cls.get_branch(branch_id, True)
        branch.is_active = False
        branch.save(update_fields=['is_active'])

    @classmethod
    def get_branch_profile(cls, branch_id: str) -> dict:
        """
        Get profile details of a branch.

        :param branch_id: ID of the branch.
        :raises ValidationError: If branch does not exist.
        :rtype: dict
        """
        branch = cls.get_branch(branch_id)
        return {
            'id': branch.id,
            'name': branch.name,
            'school_id': branch.school.id,
            'school_name': branch.school.name,
            'location': branch.location,
            'contact_email': branch.contact_email,
            'contact_phone': branch.contact_phone,
            'principal_id': branch.principal.id if branch.principal else None,
            'principal_name': branch.principal.full_name if branch.principal else None,
            'capacity': branch.capacity,
            'established_date': branch.established_date,
            'is_active': branch.is_active,
        }

    @classmethod
    def filter_branches(cls, school_id: str, **filters) -> list[dict]:
        """
        Filter and return profiles of branches for a given school.

        :param school_id: ID of the school.
        :param filters: Additional filters for branches.
        :rtype: list[dict]
        """
        school = cls.get_school(school_id)
        qs = Branch.objects.filter(school=school, is_active=True, **filters)
        return [cls.get_branch_profile(b.id) for b in qs]

    @classmethod
    def get_classroom(cls, classroom_id: str, select_for_update: bool = False) -> Classroom:
        """
        Retrieve a classroom by ID.

        :param classroom_id: ID of the classroom.
        :param select_for_update: Whether to apply row-level locking.
        :raises ValidationError: If classroom does not exist or is inactive.
        :rtype: Classroom
        """
        qs = Classroom.objects.select_related('branch')
        if select_for_update:
            qs = qs.select_for_update()
        try:
            return qs.get(id=classroom_id, is_active=True)
        except Classroom.DoesNotExist:
            raise ObjectDoesNotExist('Classroom not found')

    @classmethod
    @transaction.atomic
    def create_classroom(cls, branch_id: str, **data) -> Classroom:
        """
        Create a new classroom under a branch.

        :param branch_id: ID of the branch.
        :param data: Data for the new classroom.
        :raises ValidationError: If required fields are missing or classroom already exists.
        :rtype: Classroom
        """
        branch = cls.get_branch(branch_id)
        required_fields = {'name'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)
        if Classroom.objects.filter(branch=branch, name=data.get('name')).exists():
            raise ValidationError('Classroom already exists in this branch')
        return Classroom.objects.create(branch=branch, **data)

    @classmethod
    @transaction.atomic
    def update_classroom(cls, classroom_id: str, **data) -> Classroom:
        """
        Update an existing classroom.

        :param classroom_id: ID of the classroom.
        :param data: Fields to update.
        :raises ValidationError: If classroom does not exist or data is invalid.
        :rtype: Classroom
        """
        classroom = cls.get_classroom(classroom_id)
        allowed_fields = {'branch_id', 'name', 'capacity'}
        data = cls._sanitize_and_validate_data(data, allowed_fields=allowed_fields)
        if 'name' in data:
            if Classroom.objects.filter(branch=classroom.branch, name=data.get('name')).exclude(
                id=classroom_id
            ).exists():
                raise ValidationError('Classroom name already exists in this branch')
        for k, v in data.items():
            setattr(classroom, k, v)
        classroom.save()
        return classroom

    @classmethod
    @transaction.atomic
    def delete_classroom(cls, classroom_id: str) -> None:
        """
        Soft-delete a classroom by marking it inactive.

        :param classroom_id: ID of the classroom.
        :raises ValidationError: If classroom does not exist.
        :rtype: None
        """
        classroom = cls.get_classroom(classroom_id, True)
        classroom.is_active = False
        classroom.save(update_fields=['is_active'])

    @classmethod
    def get_classroom_profile(cls, classroom_id: str) -> dict:
        """
        Get profile details of a classroom.

        :param classroom_id: ID of the classroom.
        :raises ValidationError: If classroom does not exist.
        :rtype: dict
        """
        classroom = cls.get_classroom(classroom_id)
        return {
            'id': classroom.id,
            'name': classroom.name,
            'grade_level': classroom.grade_level,
            'capacity': classroom.capacity,
            'branch_id': classroom.branch.id,
            'branch_name': classroom.branch.name,
            'is_active': classroom.is_active,
        }

    @classmethod
    def filter_classrooms(cls, school_id: str, **filters) -> list[dict]:
        school = cls.get_school(school_id)
        filters = cls._sanitize_and_validate_data(filters)
        qs = Classroom.objects.filter(branch__school=school, is_active=True, **filters)
        return [cls.get_classroom_profile(b.id) for b in qs]
