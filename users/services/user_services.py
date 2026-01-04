import logging

from typing import Optional

from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q

from base.services.base_services import BaseServices
from notifications.models import NotificationType
from notifications.services.notification_services import NotificationServices
from schools.models import Branch, Classroom
from users.models import (
    StudentGuardian,
    User,
    Role,
    StudentProfile,
    GuardianProfile,
    TeacherProfile,
    ClerkProfile,
    AdminProfile,
    RoleName, StudentClassroomAssignment, StudentClassroomMovementType, StudentClassroomMovement
)
from utils.common import validate_password

logger = logging.getLogger(__name__)


class UserServices(BaseServices):

    profile_models = {
        'STUDENT': StudentProfile,
        'GUARDIAN': GuardianProfile,
        'TEACHER': TeacherProfile,
        'CLERK': ClerkProfile,
        'ADMIN': AdminProfile,
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
        role_name = role_name.upper()
        return Role.objects.get(name=role_name, is_active=True)

    @classmethod
    @transaction.atomic
    def _set_guardians_to_student(cls, student: User, guardians_data: list[dict]) -> None:
        StudentGuardian.objects.filter(student=student, is_active=True).update(is_active=False)
        for guardian_data in guardians_data:
            required_fields = {'guardian_id', 'relationship'}
            guardian_data = cls._sanitize_and_validate_data(guardian_data, required_fields=required_fields)
            guardian_data.setdefault('is_primary', False)
            guardian_data.setdefault('can_receive_reports', True)
            if guardian_data.get('is_primary'):
                guardian_data['can_receive_reports'] = True
            StudentGuardian.objects.update_or_create(
                student=student,
                guardian=guardian_data['guardian'],
                defaults={
                    'relationship': guardian_data['relationship'],
                    'is_primary': guardian_data['is_primary'],
                    'can_receive_reports': guardian_data['can_receive_reports'],
                    'is_active': True,
                }
            )

    @classmethod
    @transaction.atomic
    def _update_student_classroom(
            cls,
            performed_by: User,
            student: User,
            to_classroom: Optional[Classroom],
            academic_year: str,
            movement_type: str = StudentClassroomMovementType.ADMISSION,
            reason: str = ""
    ) -> None:
        current_student_classroom_assignment = StudentClassroomAssignment.objects.filter(
            student=student,
            is_current=True
        ).first()

        if current_student_classroom_assignment:
            if current_student_classroom_assignment.classroom == to_classroom and \
                    current_student_classroom_assignment.academic_year == academic_year:
                return

            current_student_classroom_assignment.is_current = False
            current_student_classroom_assignment.save(update_fields=['is_current'])

        if not movement_type in StudentClassroomMovementType.values:
            raise ValidationError('Invalid movement type')

        from_classroom = current_student_classroom_assignment.classroom \
            if current_student_classroom_assignment else None

        if to_classroom:
            StudentClassroomAssignment.objects.create(
                student=student,
                classroom=to_classroom,
                academic_year=academic_year,
                is_current=True
            )

        StudentClassroomMovement.objects.create(
            student=student,
            from_classroom=from_classroom,
            to_classroom=to_classroom,
            academic_year=academic_year,
            movement_type=movement_type,
            reason=reason,
            performed_by=performed_by
        )

    @classmethod
    @transaction.atomic
    def create_user(cls, created_by: User, role_name: str, **data) -> User:
        role = cls.get_role(role_name)

        required_fields = {'first_name', 'last_name'}
        if role.name == RoleName.STUDENT:
            required_fields.update({
                'admission_date', 'student_type'
            })
        elif role.name == RoleName.GUARDIAN:
            required_fields.update({'occupation', 'email', 'phone_number'})
        elif role.name == RoleName.TEACHER:
            required_fields.update({'tsc_number', 'email', 'phone_number'})
        elif role.name == RoleName.CLERK:
            required_fields.update({'email', 'phone_number'})
        elif role.name == RoleName.ADMIN:
            required_fields.update({'email', 'phone_number'})

        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)

        profile_model = cls.profile_models.get(role_name.upper())

        user_field_names = {f.name for f in User._meta.get_fields()}
        profile_field_names = {f.name for f in profile_model._meta.get_fields()} if profile_model else set()
        user_fields = {k: v for k, v in data.items() if k in user_field_names}
        profile_fields = {k: v for k, v in data.items() if k in profile_field_names}

        profile_model = cls.profile_models.get(role_name.upper())
        if profile_model:
            unique_fields = {
                'id_number', 'phone_number', 'email', 'tsc_number',
                'knec_number', 'nemis_number'
            }
            cls._validate_model_uniqueness(
                model=profile_model,
                data=profile_fields,
                unique_fields=unique_fields,
                self_scope={
                    'user__school': created_by.school,
                    'is_active': True,
                }
            )

        user = User.objects.create(school=created_by.school, role=role, **user_fields)

        if profile_model:
            profile_model.objects.create(user=user, **profile_fields)

        if 'branch_ids' in data:
            branches = Branch.objects.filter(
                id__in=data['branch_ids'],
                school=created_by.school,
                is_active=True
            )
            user.branches.set(branches)

        if role.name == RoleName.STUDENT:
            if data['guardians']:
                cls._set_guardians_to_student(user, data['guardians'])
            if data['classroom']:
                cls._update_student_classroom(
                    performed_by=created_by,
                    student=user,
                    to_classroom=data.get('classroom'),
                    academic_year=data.get('academic_year'),
                    movement_type=StudentClassroomMovementType.ADMISSION,
                )
                user.branches.set([data.get('classroom').branch])

            for student_guardian in user.student_guardians.filter(
                    Q(is_primary=True) | Q(can_receive_reports=True), is_active=True):
                guardian = student_guardian.guardian
                classroom = data.get('classroom')
                notification_context = {
                    "guardian_name": guardian.full_name,
                    "student_full_name": user.full_name,
                    "reg_number": user.reg_number,
                    "admission_date": user.student_profile.admission_date,
                    "academic_year": data.get('academic_year', "N/A"),
                    "classroom_name": classroom.name if classroom else None,
                }
                try:
                    NotificationServices.send_notification(
                        recipients=[guardian.guardian_profile.email],
                        notification_type=NotificationType.EMAIL,
                        template_name='email_new_student',
                        context=notification_context,
                    )

                    # NotificationServices.send_notification(
                    #     recipient=[guardian.guardian_profile.phone_number],
                    #     notification_type=NotificationType.SMS,
                    #     template_name='sms_new_student',
                    #     context=notification_context,
                    # )
                except Exception as ex:
                    logger.exception(f'Send new student notification error: {ex}')

        return user

    @classmethod
    @transaction.atomic
    def update_user(cls, updated_by: User, user_id: str, **data) -> User:
        """
        Update an existing user's fields and associated profile fields.

        :param user_id: ID of the user to update.
        :param data: Fields to update for the user and profile.
        :raises ValidationError: If user does not exist.
        :rtype: User
        """
        user = cls.get_user(user_id, select_for_update=True)

        required_fields = {'first_name', 'last_name'}
        if user.role.name == RoleName.STUDENT:
            required_fields.update({
                'admission_date', 'student_type'
            })
        elif user.role.name == RoleName.GUARDIAN:
            required_fields.update({'occupation', 'email', 'phone_number'})
        elif user.role.name == RoleName.TEACHER:
            required_fields.update({'tsc_number', 'email', 'phone_number'})
        elif user.role.name == RoleName.CLERK:
            required_fields.update({'email', 'phone_number'})
        elif user.role.name == RoleName.ADMIN:
            required_fields.update({'email', 'phone_number'})

        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)

        profile_model = cls.profile_models.get(user.role.name)

        user_field_names = {f.name for f in User._meta.get_fields()}
        profile_field_names = {f.name for f in profile_model._meta.get_fields()} if profile_model else set()
        user_fields = {k: v for k, v in data.items() if k in user_field_names}
        profile_fields = {k: v for k, v in data.items() if k in profile_field_names}

        for field, value in user_fields.items():
            setattr(user, field, value)
        user.save(update_fields=list(user_fields.keys()))

        profile = getattr(user, f'{user.role.name.lower()}_profile')
        if profile:
            unique_fields = {
                'id_number', 'phone_number', 'email', 'tsc_number',
                'knec_number', 'nemis_number'
            }
            cls._validate_model_uniqueness(
                model=profile_model,
                data=profile_fields,
                unique_fields=unique_fields,
                self_scope={
                    'user__school': user.school,
                    'is_active': True,
                },
                exclude_instance=profile
            )

            for field, value in profile_fields.items():
                setattr(profile, field, value)
            profile.save()

        if 'branch_ids' in data:
            branch_ids = data['branch_ids']
            if not branch_ids:
                user.branches.clear()
            else:
                branches = Branch.objects.filter(
                    id__in=data['branch_ids'],
                    school=user.school,
                    is_active=True
                )
                user.branches.set(branches)

        if user.role.name == RoleName.STUDENT:
            cls._set_guardians_to_student(user, data['guardians'])
            cls._update_student_classroom(
                performed_by=updated_by,
                student=user,
                to_classroom=data.get('classroom'),
                academic_year=data.get('academic_year'),
                movement_type=data.get('classroom_movement_type'),
                reason=data.get('classroom_movement_reason')
            )
            user.branches.set([data.get('classroom').branch])

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

        profile = getattr(user, f'{user.role.name.lower()}_profile', None)
        if profile:
            profile.is_active = False
            profile.save(update_fields=['is_active'])

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

        profile = getattr(user, f'{user.role.name.lower()}_profile')
        if profile:
            profile_data = {}

            for field in profile._meta.get_fields():
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

        if user.role.name == RoleName.STUDENT:
            # Attach guardians
            qs = StudentGuardian.objects.filter(
                student=user,
                is_active=True,
            ).select_related('guardian')

            profile_data['guardians'] = [
                {
                    'guardian_id': str(sg.guardian.id),
                    'guardian_name': sg.guardian.full_name,
                    'relationship': sg.relationship,
                    'is_primary': sg.is_primary,
                    'can_receive_reports': sg.can_receive_reports,
                    'phone_number': sg.guardian.guardian_profile.phone_number,
                    'email': sg.guardian.guardian_profile.email,
                    'id_number': sg.guardian.guardian_profile.id_number,
                    'occupation': sg.guardian.guardian_profile.occupation,
                }
                for sg in qs
            ]

            # Add classroom data
            classroom_assignment = StudentClassroomAssignment.objects.filter(
                student=user, is_current=True
            ).first()
            if classroom_assignment:
                classroom = classroom_assignment.classroom
                profile_data.update({
                    'classroom_id': classroom.id,
                    'classroom_name': classroom.name,
                    'grade_level': classroom.grade_level,
                    'academic_year': classroom_assignment.academic_year,
                })

            # Attach invoices
            from finances.services.invoice_services import InvoiceServices
            profile_data['invoices'] = InvoiceServices.filter_invoices(student_id=user_id)

            # Attach payments
            from finances.services.payment_services import PaymentServices
            profile_data['payments'] = PaymentServices.filter_payments(filtered_by=user, student_id=user_id)

        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'other_name': user.other_name,
            'full_name': user.full_name,
            'gender': user.gender,
            'reg_number': user.reg_number,
            'date_of_birth': user.date_of_birth,
            'town_of_residence': user.town_of_residence,
            'county_of_residence': user.county_of_residence,
            'address': user.address,
            'photo': user.photo,
            'role_id': user.role.id,
            'role_name': user.role.name,
            'school_id': user.school.id if user.school else None,
            'school_name': user.school.name if user.school else None,
            'branches': list(user.branches.all().values('id', 'name')),
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
        filters = cls._sanitize_and_validate_data(filters)

        user_ids = filters.pop('user_ids', [])
        role_names = filters.pop('role_names', [])
        branch = filters.pop('branch', None)
        search_term = filters.pop('search_term', None)
        grade_level = filters.pop('grade_level', None)
        classroom = filters.pop('classroom', None)

        base_filter = Q(is_active=True)
        if branch:
            base_filter &= Q(branches__id=branch.id)

        qs = User.objects.filter(base_filter).select_related('role', 'school').order_by('-created_at')

        user_field_names = {f.name for f in User._meta.get_fields()}
        user_filters = {k: v for k, v in filters.items() if k in user_field_names}

        role = filters.get('role')
        profile_fields = None
        if role:
            profile_model = cls.profile_models.get(role.name)
            if profile_model:
                profile_fields = profile_model._meta.get_fields()
                profile_field_names = {f.name for f in profile_fields}
                prefixed_filters = {
                    f"{role.name.lower()}_profile__{k}": v
                    for k, v in filters.items() if k in profile_field_names
                }
                user_filters.update(prefixed_filters)

        qs = qs.filter(**user_filters)

        if search_term:
            search_q = Q()

            for field in User._meta.get_fields():
                if field.is_relation and field.many_to_one:
                    search_q |= Q(**{f'{field.name}_id__icontains': search_term})
                    if hasattr(field.related_model, 'name'):
                        search_q |= Q(**{f'{field.name}__name__icontains': search_term})
                elif not field.is_relation and field.get_internal_type() in ['CharField', 'TextField']:
                    search_q |= Q(**{f'{field.name}__icontains': search_term})

            if profile_fields:
                for field in profile_fields:
                    if field.is_relation and field.many_to_one:
                        search_q |= Q(**{f'{role.name.lower()}_profile__{field.name}_id__icontains': search_term})
                        if hasattr(field.related_model, 'name'):
                            search_q |= Q(**{f'{role.name.lower()}_profile__{field.name}__name__icontains': search_term})
                    elif not field.is_relation and field.get_internal_type() in ['CharField', 'TextField']:
                        search_q |= Q(**{f'{role.name.lower()}_profile__{field.name}__icontains': search_term})

            qs = qs.filter(search_q)

        if user_ids:
            qs = qs.filter(id__in=user_ids)

        if role_names:
            roles = [cls.get_role(role_name) for role_name in role_names]
            qs = qs.filter(role__in=roles)

        if grade_level and role.name == RoleName.STUDENT:
            qs = qs.filter(
                student_classrooms__classroom__grade_level=grade_level,
                student_classrooms__is_current=True
            )

        if classroom and role.name == RoleName.STUDENT:
            qs = qs.filter(
                student_classrooms__classroom=classroom,
                student_classrooms__is_current=True
            )

        return [cls.get_user_profile(user.id) for user in qs]

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