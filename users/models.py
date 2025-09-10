import logging
import re

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import GenericBaseModel, BaseModel
from users.managers import CustomUserManager

logger = logging.getLogger(__name__)


class Role(GenericBaseModel):
    can_login = models.BooleanField(default=False, verbose_name=_('Can login'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ('name', '-date_created',)
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def student_role(cls):
        role, _ = cls.objects.get_or_create(name='student')
        return role

    @classmethod
    def guardian_role(cls):
        role, _ = cls.objects.get_or_create(name='guardian')
        return role

    @classmethod
    def teacher_role(cls):
        role, _ = cls.objects.get_or_create(name='teacher')
        return role

    @classmethod
    def clerk_role(cls):
        role, _ = cls.objects.get_or_create(name='clerk')
        return role

    @classmethod
    def admin_role(cls):
        role, _ = cls.objects.get_or_create(name='admin')
        return role


class Permission(GenericBaseModel):
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Permission')
        verbose_name_plural = _('Permissions')
        ordering = ('name', '-date_created')
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]


class RolePermission(BaseModel):
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Role')
    )
    permission = models.ForeignKey(
        Permission,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Permission')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self):
        return f'{self.role} - {self.permission}'

    class Meta:
        verbose_name = _('Role Permission')
        verbose_name_plural = _('Role Permissions')
        ordering = ('-date_created',)
        unique_together = ('role', 'permission')
        indexes = [
            models.Index(fields=['role', 'permission', 'is_active']),
        ]


class ExtendedPermission(BaseModel):
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    permission = models.ForeignKey(
        Permission,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Permission')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self):
        return f'{self.user} - {self.permission.name}'

    class Meta:
        verbose_name = _('Extended Permission')
        verbose_name_plural = _('Extended Permissions')
        ordering = ('-date_created',)
        unique_together = ('user', 'permission')
        indexes = [
            models.Index(fields=['user', 'permission', 'is_active']),
        ]


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        MALE = 'male', _('Male')
        FEMALE = 'female', _('Female')
        OTHER = 'other', _('Other')

    username = models.CharField(max_length=150, unique=True, verbose_name=_('Username'))
    first_name = models.CharField(max_length=150, blank=True, verbose_name=_('First name'))
    last_name = models.CharField(max_length=150, blank=True, verbose_name=_('Last name'))
    other_name = models.CharField(max_length=150, blank=True, verbose_name=_('Other name'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of birth'))
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.OTHER)
    reg_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name=_('Registration number'),
        help_text=_('Unique school registration number assigned to this user.'),
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_('Role'))
    branch = models.ForeignKey(
        'school.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Branch')
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_('Staff status'),
        help_text=_('Designates whether the user can log into the admin site.')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Designates whether this user should be treated as active.')
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Last activity')
    )

    USERNAME_FIELD = 'username'
    manager = CustomUserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-date_created',)
        indexes = [
            models.Index(fields=['username', 'is_active']),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.role.name})'

    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save()

    @property
    def full_name(self):
        parts = [self.first_name, self.other_name, self.last_name]
        return ' '.join(filter(None, parts))

    def generate_username(self) -> str:
        first_name = (self.first_name or '').strip().lower()
        last_name = (self.last_name or '').strip().lower()

        if first_name and last_name:
            base_username = f'{first_name}.{last_name}'
        elif first_name:
            base_username = first_name
        elif last_name:
            base_username = last_name
        else:
            base_username = 'user'

        base_username = re.sub(r'[^a-z0-9.]', '', base_username)

        if not User.objects.filter(username=base_username, is_active=True).exists():
            return base_username

        counter = 2
        while True:
            username = f'{base_username}{counter:02d}'
            if not User.objects.filter(username=username, is_active=True).exists():
                return username
            counter += 1

    def generate_reg_number(self) -> str:
        role_prefixes = {
            'student': 'STU',
            'teacher': 'TCH',
            'clerk': 'CLK',
            'admin': 'ADM',
            'guardian': 'GDN',
        }

        if self.branch:
            school_code = self.branch.school.code
        else:
            school_code = 'SCH'

        role_key = self.role.name.lower()
        role_prefix = role_prefixes.get(role_key, 'USR')

        prefix = f'{school_code}-{role_prefix}'

        last_code = User.objects.filter(
            reg_number__startswith=prefix
        ).aggregate(max_code=Max('reg_number'))['max_code']

        if last_code:
            try:
                last_number = int(last_code.split('-')[-1])
            except ValueError:
                last_number = 0
            new_number = last_number + 1
        else:
            new_number = 1

        return f'{prefix}-{str(new_number).zfill(4)}'

    def save(self, *args, **kwargs):
        if not self.role:
            raise ValueError("User's role must be provided")
        if not self.username:
            self.username = self.generate_username()
        if not self.reg_number:
            self.reg_number = self.generate_reg_number()
        super().save(*args, **kwargs)

    @property
    def permissions(self):
        try:
            if self.is_superuser:
                return list(
                    Permission.objects.filter(is_active=True)
                    .values_list('name', flat=True)
                )

            role_permissions = RolePermission.objects.filter(
                role=self.role,
                permission__is_active=True,
                is_active=True
            ).values_list('permission__name', flat=True)

            extended_permissions = ExtendedPermission.objects.filter(
                user=self,
                permission__is_active=True,
                is_active=True
            ).values_list('permission__name', flat=True)

            permissions = list(set(role_permissions).union(extended_permissions))

            return permissions

        except Exception as e:
            logger.exception('User model - get_permissions exception: %s' % e)
            return []


class StudentGuardian(BaseModel):
    class Relationship(models.TextChoices):
        FATHER = 'father', _('Father')
        MOTHER = 'mother', _('Mother')
        GUARDIAN = 'guardian', _('Guardian')
        UNCLE = 'uncle', _('Uncle')
        AUNT = 'aunt', _('Aunt')
        BROTHER = 'brother', _('Brother')
        SISTER = 'sister', _('Sister')
        GRANDFATHER = 'grandfather', _('Grandfather')
        GRANDMOTHER = 'grandmother', _('Grandmother')
        OTHER = 'other', _('Other')

    student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='student_guardians',
        verbose_name=_('Student'),
    )
    guardian = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='guardian_students',
        verbose_name=_('Guardian'),
    )
    relationship = models.CharField(
        max_length=20,
        blank=True,
        choices=Relationship.choices,
        default=Relationship.OTHER,
        verbose_name=_('Relationship'),
        help_text=_("The guardian's relationship to the student."),
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Primary guardian'),
        help_text=_("Indicates whether this is the student's primary guardian."),
    )

    class Meta:
        unique_together = ('student', 'guardian')
        verbose_name = _('Student guardian')
        verbose_name_plural = _('Student guardians')
        ordering = ('-date_created',)

    def __str__(self):
        return f'{self.guardian} - {self.relationship} of {self.student}'


class StudentProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('User')
    )
    knec_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name=_('KNEC number')
    )
    nemis_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name=_('NEMIS number')
    )
    classroom = models.ForeignKey(
        'school.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_('Classroom')
    )
    guardians = models.ManyToManyField(
        User,
        through=StudentGuardian,
        related_name='guarded_students',
        verbose_name=_('Guardians'),
    )
    medical_info = models.TextField(blank=True, null=True, verbose_name=_('Medical information'))
    additional_info = models.TextField(blank=True, null=True, verbose_name=_('Additional information'))

    class Meta:
        verbose_name = _('Student Profile')
        verbose_name_plural = _('Student Profiles')
        ordering = ('-date_created',)

    def __str__(self):
        return f'Profile for {self.user}'

    def clean(self):
        if self.user.role != Role.student_role():
            raise ValidationError(_("User must have role 'student' for StudentProfile."))
        if self.classroom and self.user.branch != self.classroom.branch:
            raise ValidationError(_("Classroom must belong to the user's branch."))


class GuardianProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guardian_profile',
        verbose_name=_('User'),
    )
    id_number = models.CharField(max_length=20, unique=True, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=20, unique=True, verbose_name=_('Phone number'))
    email = models.EmailField(unique=True, blank=True, verbose_name=_('Email address'))
    occupation = models.CharField(max_length=100, blank=True, verbose_name=_('Occupation'))

    class Meta:
        verbose_name = _('Guardian Profile')
        verbose_name_plural = _('Guardian Profiles')
        ordering = ('-date_created',)

    def __str__(self):
        return f'Guardian Profile for {self.user}'

    def clean(self):
        if self.user.role != Role.guardian_role():
            raise ValidationError(_("User must have role 'guardian' for GuardianProfile."))


class TeacherProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('User')
    )
    tsc_number = models.CharField(max_length=50, unique=True, verbose_name=_('TSC number'))
    id_number = models.CharField(max_length=20, unique=True, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone number'))
    email = models.EmailField(unique=True, blank=True, verbose_name=_('Email address'))

    class Meta:
        verbose_name = _('Teacher Profile')
        verbose_name_plural = _('Teacher Profiles')
        ordering = ('-date_created',)

    def __str__(self):
        return f'Profile for {self.user}'

    def clean(self):
        if self.user.role.name != 'teacher':
            raise ValidationError(_("User must have role 'teacher' for TeacherProfile."))


class ClerkProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='clerk_profile',
        verbose_name=_('User')
    )
    id_number = models.CharField(max_length=20, unique=True, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=12, blank=True, unique=True, verbose_name=_('Phone number'))
    email = models.EmailField(unique=True, blank=True, verbose_name=_('Email address'))

    class Meta:
        verbose_name = _('Clerk Profile')
        verbose_name_plural = _('Clerk Profiles')
        ordering = ('-date_created',)

    def __str__(self):
        return f'Profile for {self.user}'

    def clean(self):
        if self.user.role != Role.clerk_role():
            raise ValidationError(_("User must have role 'clerk' for ClerkProfile."))


class AdminProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name=_('User')
    )
    id_number = models.CharField(max_length=20, blank=True, unique=True, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=12, blank=True, unique=True, verbose_name=_('Phone number'))
    email = models.EmailField(unique=True, blank=True, verbose_name=_('Email address'))

    class Meta:
        verbose_name = _('Admin Profile')
        verbose_name_plural = _('Admin Profiles')
        ordering = ('-date_created',)

    def __str__(self):
        return f'Profile for {self.user}'

    def clean(self):
        if self.user.role != Role.admin_role():
            raise ValidationError(_("User must have role 'admin' for AdminProfile."))


class Device(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255)
    last_activity = models.DateTimeField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        return f'{self.user.username} ({status})'

    class Meta(object):
        ordering = ('-date_created',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'token'], name='unique_user_token')
        ]
        indexes = [
            models.Index(fields=['token']),
        ]
