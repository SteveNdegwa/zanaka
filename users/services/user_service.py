import logging
from typing import Optional

from django.apps import apps
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q

from users.models import (
    StudentGuardian, User, Role, StudentProfile, GuardianProfile, TeacherProfile,
    ClerkProfile, AdminProfile
)

logger = logging.getLogger(__name__)


class UserService:
    profile_models = {
        'student': StudentProfile,
        'guardian': GuardianProfile,
        'teacher': TeacherProfile,
        'clerk': ClerkProfile,
        'admin': AdminProfile,
    }

    fk_mappings = {
        'branch_id': ('school.Branch', 'branch'),
        'classroom_id': ('school.Classroom', 'classroom'),
        'role': ('users.Role', 'role')
    }

    @classmethod
    def _resolve_foreign_keys(cls, data: dict) -> dict:
        resolved = {}

        for field, value in data.items():
            if field in cls.fk_mappings and value:
                model_path, attr = cls.fk_mappings[field]
                model = apps.get_model(model_path)

                try:
                    resolved[attr] = model.objects.get(id=value, is_active=True)
                except ObjectDoesNotExist:
                    raise ValidationError(
                        f'{attr} with id={value} does not exist or is inactive.'
                    )
            else:
                resolved[field] = value

        return resolved

    @classmethod
    def get_user(cls, user_id: str, role_name: Optional[Role.RoleName] = None) -> User:
        filters = {'id': user_id, 'is_active': True}
        if role_name:
            filters['role__name'] = role_name

        user = User.objects.get(**filters, select_related=['role'])
        return user

    @classmethod
    @transaction.atomic
    def create_user(cls, role_name: str, **data) -> User:
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'branch_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f'Missing required field: {field}')

        role = Role.objects.get(name=role_name.lower(), is_active=True)
        data = cls._resolve_foreign_keys(data)

        user_fields = {k: v for k, v in data.items() if k in User._meta.fields_map}
        profile_fields = {k: v for k, v in data.items() if k not in user_fields}

        profile_model = cls.profile_models.get(role_name.lower())

        if profile_model:
            unique_field_names = [
                f.name for f in profile_model._meta.fields if f.unique
            ]
            for field_name in unique_field_names:
                if field_name in profile_fields:
                    existing = profile_model.objects.filter(
                        **{field_name: profile_fields[field_name]},
                        user__is_active=True
                    ).exists()
                    if existing:
                        raise ValidationError(
                            f'{role_name.capitalize()} with {field_name}="{profile_fields[field_name]}" already exists.'
                        )

        user = User.objects.create(role=role, **user_fields)

        if profile_model:
            profile_model.objects.create(user=user, **profile_fields)

        return user

    @classmethod
    @transaction.atomic
    def update_user(cls, user_id: str, **data) -> User:
        user = cls.get_user(user_id)
        data = cls._resolve_foreign_keys(data)

        user_fields = {k: v for k, v in data.items() if k in User._meta.fields_map}
        for field, value in user_fields.items():
            setattr(user, field, value)
        user.save()

        if hasattr(user, f'{user.role.name.lower()}_profile'):
            profile = getattr(user, f'{user.role.name.lower()}_profile')
            profile_fields = {k: v for k, v in data.items() if k not in user_fields}
            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.save()

        return user

    @classmethod
    @transaction.atomic
    def delete_user(cls, user_id: str) -> None:
        user = cls.get_user(user_id)
        user.is_active = False
        user.save()

    @classmethod
    @transaction.atomic
    def add_guardian_to_student(
            cls,
            student_id: str,
            guardian_id: str,
            relationship: str,
            is_primary: bool = False,
            can_receive_reports: bool = True
    ) -> StudentGuardian:
        student = cls.get_user(user_id=student_id, role_name=Role.RoleName.STUDENT)
        guardian = cls.get_user(user_id=guardian_id, role_name=Role.RoleName.GUARDIAN)

        sg, created = StudentGuardian.objects.update_or_create(
            student=student,
            guardian=guardian,
            defaults={
                'relationship': relationship,
                'is_primary': is_primary,
                'can_receive_reports': can_receive_reports,
                'is_active': True
            }
        )

        if sg.is_primary:
            StudentGuardian.objects.filter(
                student=student,
                is_primary=True
            ).exclude(id=sg.id).update(is_primary=False)

        return sg

    @classmethod
    @transaction.atomic
    def remove_guardian_from_student(cls, student_id: str, guardian_id: str) -> None:
        student = cls.get_user(student_id)
        guardian = cls.get_user(guardian_id)

        sg = StudentGuardian.objects.get(student=student, guardian=guardian)
        sg.is_active = False
        sg.save()

    @classmethod
    def get_user_profile(cls, user_id: str) -> dict:
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

            if user.role.name == Role.RoleName.STUDENT:
                profile_data["guardians"] = [
                    cls.get_user_profile(guardian.id) for guardian in profile.guardians
                ]

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
            'branch_id': user.branch.id,
            'branch_name': user.branch.name,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser,
            'permissions': user.permissions,
        }

        return {**user_data, **profile_data}

    @classmethod
    def filter_users(cls, **filters) -> list[dict]:
        resolved_filters = cls._resolve_foreign_keys(filters.copy())

        search_term = resolved_filters.pop('search', None)

        user_field_names = set(User._meta.fields_map.keys())
        user_filters = {k: v for k, v in resolved_filters.items() if k in user_field_names}
        profile_filters = {k: v for k, v in resolved_filters.items() if k not in user_field_names}

        qs = User.objects.filter(is_active=True, **user_filters).select_related('role', 'branch')

        if profile_filters:
            role = resolved_filters.get('role')
            if not role:
                raise ValidationError('Role is required when filtering by profile fields')
            qs = qs.filter(**{f'{role.name.lower()}_profile__{k}': v for k, v in profile_filters.items()})

        if search_term:
            role = resolved_filters.get('role')
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
