from typing import Optional

from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q

from base.services.base_services import BaseServices
from users.models import (
    StudentGuardian,
    User,
    Role,
    StudentProfile,
    GuardianProfile,
    TeacherProfile,
    ClerkProfile,
    AdminProfile, RoleName
)
from utils.common import validate_password


class UserServices(BaseServices):

    profile_models = {
        'student': StudentProfile,
        'guardian': GuardianProfile,
        'teacher': TeacherProfile,
        'clerk': ClerkProfile,
        'admin': AdminProfile,
    }

    fk_mappings = {
        'branch_id': ('schools.Branch', 'branch'),
        'classroom_id': ('schools.Classroom', 'classroom'),
        'role_name': ('users.Role', 'role'),
        'guardian_id': ('users.User', 'guardian')
    }

    UNIQUE_FIELDS = ['username', 'reg_number']

    @classmethod
    def get_user_by_credential(cls, credential: str) -> tuple[Optional[User], Optional[str]]:
        """
        Retrieve a user using a unique credential (username, ID number, email, or phone number).

        :param credential: The credential to search for.
        :type credential: str
        :return: Tuple containing the user instance (if found) and the matched field label.
        :rtype: tuple[Optional[User], Optional[str]]
        """
        filters = Q()
        for field in cls.UNIQUE_FIELDS:
            filters |= Q(**{field.lower(): credential})

        user = User.objects.filter(filters, is_active=True).first()
        if not user:
            return None, None

        # Determine which field matched the credential
        for field in cls.UNIQUE_FIELDS:
            if getattr(user, field, None) == credential:
                field_label = field.replace('_', '' '').capitalize()
                return user, field_label

        return user, None

    @classmethod
    def get_user(cls, user_id: str, role_name: Optional[str] = None, select_for_update=False) -> User:
        """
        Retrieve an active user by ID and optionally role.

        :param user_id: The ID of the user to retrieve.
        :param role_name: Optional role name to filter the user.
        :param select_for_update: Whether to lock the row for update.
        :raises ValidationError: If the user or role-specific user does not exist.
        :rtype: User
        """
        filters = Q(id=user_id, is_active=True)
        if role_name:
            role = cls.get_role(role_name)
            filters &= Q(role=role)

        qs = User.objects.select_related('role')
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    def get_role(cls, role_name: str) -> Role:
        """
        Retrieve an active role by name.

        :param role_name: Name of the role.
        :raises ValidationError: If the role does not exist.
        :rtype: Role
        """
        role_name = role_name.lower()
        return Role.objects.get(name=role_name, is_active=True)

    @classmethod
    def _validate_profile_uniqueness(cls, profile_model, profile_fields: dict) -> None:
        """
        Ensure unique fields in the profile model do not already exist.

        :param profile_model: The profile model class.
        :param profile_fields: Fields for the profile.
        :raises ValidationError: If a unique field already exists.
        """
        role_label = profile_model.__name__
        for field in profile_model._meta.fields:
            if field.unique and field.name in profile_fields:
                value = profile_fields[field.name]
                if profile_model.objects.filter(**{field.name: value}, user__is_active=True).exists():
                    raise ValidationError(
                        f"{role_label} with {field.name}='{value}' already exists."
                    )

    @classmethod
    @transaction.atomic
    def create_user(cls, role_name: str, **data) -> User:
        """
        Create a new user with associated profile if applicable.

        :param role_name: Name of the role for the user.
        :param data: User and profile fields.
        :raises ValidationError: If required fields are missing or profile uniqueness is violated.
        :rtype: User
        """
        role = cls.get_role(role_name)
        required_fields = {'first_name', 'last_name', 'date_of_birth', 'branch_id'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)

        user_field_names = {f.name for f in User._meta.get_fields()}
        user_fields = {k: v for k, v in data.items() if k in user_field_names}
        profile_fields = {k: v for k, v in data.items() if k not in user_field_names}

        profile_model = cls.profile_models.get(role_name.lower())
        if profile_model:
            cls._validate_profile_uniqueness(profile_model, profile_fields)

        user = User.objects.create(role=role, **user_fields)

        if profile_model:
            profile_model.objects.create(user=user, **profile_fields)

        return user

    @classmethod
    @transaction.atomic
    def update_user(cls, user_id: str, **data) -> User:
        """
        Update an existing user's fields and associated profile fields.

        :param user_id: ID of the user to update.
        :param data: Fields to update for the user and profile.
        :raises ValidationError: If user does not exist.
        :rtype: User
        """
        user = cls.get_user(user_id, select_for_update=True)

        allowed_fields = {
            'first_name', 'last_name', 'other_name', 'date_of_birth',
            'gender', 'reg_number', 'branch_id', 'knec_number',
            'nemis_number', 'classroom_id', 'medical_info',
            'additional_info', 'id_number', 'phone_number', 'email',
            'occupation', 'tsc_number',
        }
        data = cls._sanitize_and_validate_data(data, allowed_fields=allowed_fields)

        user_fields = {k: v for k, v in data.items() if k in User._meta.fields_map}
        for field, value in user_fields.items():
            setattr(user, field, value)
        user.save()

        if hasattr(user, f'{user.role.name.lower()}_profile'):
            profile = getattr(user, f'{user.role.name.lower()}_profile')
            profile_fields = {k: v for k, v in data.items() if k not in user_fields}
            profile_model = cls.profile_models.get(user.role.name.lower())
            if profile_model:
                cls._validate_profile_uniqueness(profile_model, profile_fields)
            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.save()

        return user

    @classmethod
    @transaction.atomic
    def delete_user(cls, user_id: str) -> None:
        """
        Deactivate a user instead of deleting.

        :param user_id: ID of the user to deactivate.
        :raises ValidationError: If user does not exist.
        """
        user = cls.get_user(user_id, select_for_update=True)
        user.is_active = False
        user.save(update_fields=['is_active'])

    @classmethod
    def get_user_profile(cls, user_id: str) -> dict:
        """
        Get a dictionary representation of a user's fields and profile fields.

        :param user_id: ID of the user.
        :raises ValidationError: If user does not exist.
        :rtype: dict
        """
        user = cls.get_user(user_id)
        profile_data = {}

        if hasattr(user, f'{user.role.name.lower()}_profile'):
            profile = getattr(user, f'{user.role.name.lower()}_profile')
            profile_data = {}

            for field in profile._meta.fields:
                if field.name in {'id', 'user'}:
                    continue

                value = getattr(profile, field.name)

                if field.is_relation and field.many_to_one:
                    related_obj = value
                    if related_obj:
                        profile_data[f'{field.name}_id'] = related_obj.id
                        if hasattr(related_obj, 'name'):
                            profile_data[f'{field.name}_name'] = related_obj.name
                    else:
                        profile_data[field.name] = None
                else:
                    profile_data[field.name] = value

        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'other_name': user.other_name,
            'gender': user.gender,
            'reg_number': user.reg_number,
            'date_of_birth': user.date_of_birth,
            'role_id': user.role.id,
            'role_name': user.role.name,
            'branch_id': user.branch.id if user.branch else None,
            'branch_name': user.branch.name if user.branch else None,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'force_pass_reset': user.force_pass_reset,
            'permissions': user.permissions,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
        }

        return {**user_data, **profile_data}

    @classmethod
    def filter_users(cls, **filters) -> list[dict]:
        """
        Filter active users by user or profile fields with optional search term.

        :param filters: Dictionary of fields to filter on, may include 'search'.
        :raises ValidationError: If role is missing when filtering by profile fields.
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        search_term = filters.pop('search', None)

        user_field_names = set(User._meta.fields_map.keys())
        user_filters = {k: v for k, v in filters.items() if k in user_field_names}
        profile_filters = {k: v for k, v in filters.items() if k not in user_field_names}

        qs = User.objects.filter(is_active=True, **user_filters).select_related('role', 'branch')

        if profile_filters:
            role = filters.get('role')
            if not role:
                raise ValidationError('Role is required when filtering by profile fields')
            qs = qs.filter(**{f'{role.name.lower()}_profile__{k}': v for k, v in profile_filters.items()})

        if search_term:
            role = filters.get('role')
            search_q = Q()
            for field in User._meta.fields:
                if field.is_relation and field.many_to_one:
                    search_q |= Q(**{f'{field.name}_id__icontains': search_term})
                    if hasattr(field.related_model, 'name'):
                        search_q |= Q(**{f'{field.name}__name__icontains': search_term})
                elif not field.is_relation and field.get_internal_type() in ['CharField', 'TextField']:
                    search_q |= Q(**{f'{field.name}__icontains': search_term})

            if role:
                profile_model = f'{role.name.lower()}_profile'
                model_class = getattr(User, profile_model).field.related_model

                for field in model_class._meta.fields:
                    if field.is_relation and field.many_to_one:
                        search_q |= Q(**{f'{profile_model}__{field.name}_id__icontains': search_term})
                        if hasattr(field.related_model, 'name'):
                            search_q |= Q(**{f'{profile_model}__{field.name}__name__icontains': search_term})
                    elif not field.is_relation and field.get_internal_type() in ['CharField', 'TextField']:
                        search_q |= Q(**{f'{profile_model}__{field.name}__icontains': search_term})

            qs = qs.filter(search_q)

        return [cls.get_user_profile(user.id) for user in qs]

    @classmethod
    @transaction.atomic
    def add_guardian_to_student(cls, student_id: str, **data) -> StudentGuardian:
        """
        Link a guardian to a student.

        :param student_id: ID of the student.
        :param data: 'guardian_id' and 'relationship' fields.
        :raises ValidationError: If guardian already linked or required fields missing.
        :rtype: StudentGuardian
        """
        student = cls.get_user(student_id, role_name=RoleName.STUDENT)
        required_fields = {'guardian_id', 'relationship'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)
        data.setdefault('is_primary', False)
        data.setdefault('can_receive_reports', True)
        if data.get('is_primary'): data['can_receive_reports'] = True
        if StudentGuardian.objects.filter(student=student, guardian=data.get('guardian'), is_active=True).exists():
            raise ValidationError('Guardian already linked to student')
        return StudentGuardian.objects.create(student=student, **data)

    @classmethod
    @transaction.atomic
    def remove_guardian_from_student(cls, student_id: str, guardian_id: str) -> None:
        """
        Unlink a guardian from a student.

        :param student_id: ID of the student.
        :param guardian_id: ID of the guardian.
        :raises ValidationError: If guardian not linked to student.
        """
        student = cls.get_user(student_id, role_name=RoleName.STUDENT)
        guardian = cls.get_user(guardian_id, role_name=RoleName.GUARDIAN)
        try:
            sg = StudentGuardian.objects.get(student=student, guardian=guardian, is_active=True)
        except StudentGuardian.DoesNotExist:
            raise ValidationError('Guardian not linked to student')
        sg.is_active = False
        sg.save(update_fields=['is_active'])

    @classmethod
    def filter_guardians_for_student(cls, student_id: str, **filters) -> list[dict]:
        """
        List all active guardians for a student with optional filters.

        :param student_id: ID of the student.
        :param filters: Optional filters for the StudentGuardian queryset.
        :rtype: list[dict]
        """
        student = cls.get_user(student_id, role_name=RoleName.STUDENT)
        qs = StudentGuardian.objects.filter(
            student=student,
            is_active=True,
            **filters
        ).select_related('guardian')

        return [
            {
                'guardian_id': sg.guardian.id,
                'guardian_name': sg.guardian.full_name,
                'relationship': sg.relationship,
                'is_primary': sg.is_primary,
                'can_receive_reports': sg.can_receive_reports,
            }
            for sg in qs
        ]

    @classmethod
    @transaction.atomic
    def forgot_password(cls, credential: str) -> None:
        """
        Reset a user's password based on their credential and send it via Email.

        :param credential: The credential to identify the user.
        :type credential: str
        :return: None
        :raises Exception: If the user is not found.
        """
        user, _ = cls.get_user_by_credential(credential)
        if not user:
            raise ObjectDoesNotExist('User not found')
        user.reset_password()
        return None

    @classmethod
    @transaction.atomic
    def reset_password(cls, user_id: str) -> None:
        """
        Reset a user's password using their ID and send it via Email.

        :param user_id: The ID of the user.
        :type user_id: str
        :return: None
        :raises Exception: If the user is not found.
        """
        user = cls.get_user(user_id)
        user.reset_password()
        return None

    @classmethod
    @transaction.atomic
    def change_password(cls, user_id: str, current_password: str, new_password: str) -> None:
        """
        Change a user's password after verifying the old password.

        :param user_id: The ID of the user.
        :type user_id: str
        :param current_password: The current password for verification.
        :type current_password: str
        :param new_password: The new password.
        :type new_password: str
        :return: None
        :raises ValueError: If the user is not found or the old password is incorrect.
        """
        user = cls.get_user(user_id)

        if not user.check_password(current_password):
            raise ValidationError('Incorrect password')

        valid, error = validate_password(new_password)
        if not valid:
            raise ValidationError(error)

        user.set_password(new_password)
        user.force_pass_reset = False
        user.save()

        return None