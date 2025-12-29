import re

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import make_password, identify_hasher
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import GenericBaseModel, BaseModel
from users.managers import CustomUserManager
from utils.common import generate_random_password


class RoleName(models.TextChoices):
    STUDENT = 'STUDENT', _('Student')
    GUARDIAN = 'GUARDIAN', _('Guardian')
    TEACHER = 'TEACHER', _('Teacher')
    CLERK = 'CLERK', _('Clerk')
    ADMIN = 'ADMIN', _('Admin')


class Gender(models.TextChoices):
    MALE = 'MALE', _('Male')
    FEMALE = 'FEMALE', _('Female')
    OTHER = 'OTHER', _('Other')


class StudentType(models.TextChoices):
    DAY_SCHOLAR = 'DAY_SCHOLAR', _('Day Scholar')
    BOARDER = 'BOARDER', _('Boarder')


class GuardianRelationship(models.TextChoices):
    FATHER = 'FATHER', _('Father')
    MOTHER = 'MOTHER', _('Mother')
    GUARDIAN = 'GUARDIAN', _('Guardian')
    UNCLE = 'UNCLE', _('Uncle')
    AUNT = 'AUNT', _('Aunt')
    BROTHER = 'BROTHER', _('Brother')
    SISTER = 'SISTER', _('Sister')
    GRANDFATHER = 'GRANDFATHER', _('Grandfather')
    GRANDMOTHER = 'GRANDMOTHER', _('Grandmother')
    OTHER = 'OTHER', _('Other')


class StudentClassroomMovementType(models.TextChoices):
    ADMISSION = 'ADMISSION', _('Admission')
    PROMOTION = 'PROMOTION', _('Promotion')
    STREAM_CHANGE = 'STREAM_CHANGE', _('Stream change')
    REPEAT = 'REPEAT', _('Repeat')
    TRANSFER_OUT = 'TRANSFER_OUT', _('Transfer out')
    GRADUATION = 'GRADUATION', _('Graduation')
    WITHDRAWAL = 'WITHDRAWAL', _('Withdrawal')


class StudentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    GRADUATED = 'GRADUATED', _('Graduated')
    TRANSFERRED = 'TRANSFERRED', _('Transferred')


class TeacherStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    RETIRED = 'RETIRED', _('Retired')
    TERMINATED = 'TERMINATED', _('Terminated')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')


class GuardianStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')


class ClerkStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    TERMINATED = 'TERMINATED', _('Terminated')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')


class AdminStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    TERMINATED = 'TERMINATED', _('Terminated')
    ON_LEAVE = 'ON_LEAVE', _('On Leave')


class Role(GenericBaseModel):
    name = models.CharField(
        max_length=50,
        unique=True,
        choices=RoleName.choices,
        verbose_name=_('Name'),
    )
    can_login = models.BooleanField(default=False, verbose_name=_('Can login'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ('name', '-created_at',)
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def __str__(self) -> str:
        return self.name


class Permission(GenericBaseModel):
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = _('Permission')
        verbose_name_plural = _('Permissions')
        ordering = ('name', '-created_at')
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

    def __str__(self) -> str:
        return f'{self.role} - {self.permission}'

    class Meta:
        verbose_name = _('Role Permission')
        verbose_name_plural = _('Role Permissions')
        ordering = ('-created_at',)
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

    def __str__(self) -> str:
        return f'{self.user} - {self.permission.name}'

    class Meta:
        verbose_name = _('Extended Permission')
        verbose_name_plural = _('Extended Permissions')
        ordering = ('-created_at',)
        unique_together = ('user', 'permission')
        indexes = [
            models.Index(fields=['user', 'permission', 'is_active']),
        ]


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, verbose_name=_('Username'))
    first_name = models.CharField(max_length=150, blank=True, verbose_name=_('First name'))
    last_name = models.CharField(max_length=150, blank=True, verbose_name=_('Last name'))
    other_name = models.CharField(max_length=150, blank=True, verbose_name=_('Other name'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of birth'))
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.OTHER)
    town_of_residence = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Town of residence'))
    county_of_residence = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('County of residence'))
    address = models.TextField(blank=True, null=True, verbose_name=_('Address'))
    reg_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name=_('Registration number'),
        help_text=_('Unique school registration number assigned to this user.'),
    )
    photo = models.TextField(blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_('Role'))
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('School')
    )
    branches = models.ManyToManyField(
        'schools.Branch',
        blank=True,
        related_name='assigned_users',
        verbose_name=_('Assigned Branches'),
        help_text=_(
            "Branches this user is assigned to. "
            "Leave blank for access to ALL branches in the school."
        )
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
    force_pass_reset = models.BooleanField(
        default=False,
        verbose_name=_('Force password reset'),
        help_text=_("User must update password on next login.")
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name=_('Last activity')
    )

    USERNAME_FIELD = 'username'

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['username', 'is_active']),
        ]

    def __str__(self) -> str:
        return f'{self.full_name} ({self.role.name})'

    def update_last_activity(self) -> None:
        self.last_activity = timezone.now()
        self.save()

    @property
    def full_name(self) -> str:
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

        if self.school:
            school_code = self.school.code
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

    def reset_password(self) -> None:
        if not self.role.can_login:
            raise PermissionDenied()
        new_password = generate_random_password()
        self.password = make_password(new_password)
        self.force_pass_reset = True

        from notifications.services.notification_services import NotificationServices
        from notifications.models import NotificationType
        notification_context = {'name': self.first_name, 'password': new_password}
        NotificationServices.send_notification(
            user=self,
            notification_type=NotificationType.EMAIL,
            template_name='email_reset_password',
            context=notification_context
        )

        self.save()

    def save(self, *args, **kwargs) -> None:
        notification_context = {}

        # Ensure role is provided
        if not self.role:
            raise ValueError("User's role must be provided")

        # Ensure first name is provided
        if not self.first_name:
            if not self.is_superuser:
                raise ValueError("User's first name must be provided")
            else:
                self.first_name = self.username.title().strip()

        # Generate username if not provided
        if not self.username:
            self.username = self.generate_username()

        # Generate phone number if not provided
        if not self.reg_number:
            self.reg_number = self.generate_reg_number()

        # Generate password if not provided
        if not self.password:
            password = generate_random_password()
            self.password = make_password(password)
            notification_context['password'] = password

        # Ensure password is hashed
        # noinspection PyBroadException
        try:
            identify_hasher(self.password)
        except:
            self.password = make_password(self.password)

        # Save
        super().save(*args, **kwargs)

        # Send notification if creating new user
        if self._state.adding and self.role.can_login:
            notification_context['name'] = self.first_name
            from notifications.services.notification_services import NotificationServices
            from notifications.models import NotificationType
            NotificationServices.send_notification(
                user=self,
                notification_type=NotificationType.EMAIL,
                template_name="email_new_user",
                context=notification_context
            )

    @property
    def permissions(self) -> list[str]:
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

    def has_permission(self, permission_name) -> bool:
        return permission_name in self.permissions


class StudentGuardian(BaseModel):
    student = models.ForeignKey(
        User,
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
        choices=GuardianRelationship.choices,
        default=GuardianRelationship.OTHER,
        verbose_name=_('Relationship'),
        help_text=_("The guardian's relationship to the student."),
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name=_('Primary guardian'),
        help_text=_("Indicates whether this is the student's primary guardian."),
    )
    can_receive_reports = models.BooleanField(
        default=True,
        verbose_name=_('Can receive reports'),
        help_text=_("Authorized to receive student notifications and communications."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        unique_together = ('student', 'guardian')
        verbose_name = _('Student guardian')
        verbose_name_plural = _('Student guardians')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'{self.guardian} - {self.relationship} of {self.student}'

    def save(self, *args, **kwargs) -> None:
        if self.is_primary:
            self.receive_notifications = True

        self.full_clean()
        super().save(*args, **kwargs)


class StudentClassroomAssignment(BaseModel):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_classrooms',
        verbose_name=_('Student'),
    )
    classroom = models.ForeignKey(
        'schools.Classroom',
        on_delete=models.CASCADE,
        related_name='classroom_students',
        verbose_name=_('Classroom'),
    )
    academic_year = models.CharField(max_length=20, verbose_name=_('Academic year'))
    is_current = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Student Classroom')
        verbose_name_plural = _('Student Classrooms')
        ordering = ('-created_at',)
        unique_together = ('student', 'is_current')

    def __str__(self) -> str:
        return f'{self.student} in {self.classroom}'


class StudentClassroomMovement(BaseModel):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='classroom_movements',
        verbose_name=_('Student'),
    )
    from_classroom = models.ForeignKey(
        'schools.Classroom',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_('From Classroom')
    )
    to_classroom = models.ForeignKey(
        'schools.Classroom',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_('To Classroom')
    )
    academic_year = models.CharField(max_length=20, verbose_name=_('Academic year'))
    movement_type = models.CharField(
        max_length=30,
        choices=StudentClassroomMovementType.choices,
        verbose_name=_('Movement Type')
    )
    reason = models.TextField(blank=True, verbose_name=_('Reason'))
    performed_by = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='performed_movements',
        verbose_name=_('Performed By')
    )

    class Meta:
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['academic_year']),
            models.Index(fields=['movement_type']),
        ]


class StudentProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('User')
    )
    student_type = models.CharField(
        max_length=20,
        choices=StudentType.choices,
        blank=True,
        null=True,
        verbose_name=_('Student Type'),
        help_text=_('Indicates whether the student is a day scholar or a boarder.')
    )
    knec_number = models.CharField(max_length=50, blank=True, verbose_name=_('KNEC number'))
    nemis_number = models.CharField(max_length=50, blank=True, verbose_name=_('NEMIS number'))
    subscribed_to_transport = models.BooleanField(
        default=False,
        verbose_name=_('Subscribed to school transport'),
        help_text=_('Whether the student uses school-provided transport.')
    )
    subscribed_to_meals = models.BooleanField(
        default=False,
        verbose_name=_('Subscribed to school meals'),
        help_text=_('Whether the student is enrolled in the school feeding program.')
    )
    medical_info = models.TextField(blank=True, null=True, verbose_name=_('Medical information'))
    additional_info = models.TextField(blank=True, null=True, verbose_name=_('Additional information'))
    admission_date = models.DateField(null=True, blank=True, verbose_name=_('Admission date'))
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'),)

    class Meta:
        verbose_name = _('Student Profile')
        verbose_name_plural = _('Student Profiles')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Profile for {self.user}'

    def clean(self) -> None:
        if self.user.role.name != RoleName.STUDENT:
            raise ValidationError(_("User must have role 'student' for StudentProfile."))

        if self.student_type == StudentType.BOARDER:
            self.subscribed_to_meals = False
            self.subscribed_to_transport = False

    @property
    def guardians(self) -> list[User]:
        relationships = StudentGuardian.objects.filter(
            student=self.user,
            is_active=True
        ).order_by('-is_primary', 'created_at')
        return [rel.guardian for rel in relationships]


class GuardianProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guardian_profile',
        verbose_name=_('User'),
    )
    id_number = models.CharField(max_length=20, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=20, verbose_name=_('Phone number'))
    email = models.EmailField(blank=True, verbose_name=_('Email address'))
    occupation = models.CharField(max_length=100, blank=True, verbose_name=_('Occupation'))
    status = models.CharField(
        max_length=20,
        choices=GuardianStatus.choices,
        default=GuardianStatus.ACTIVE,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'), )

    class Meta:
        verbose_name = _('Guardian Profile')
        verbose_name_plural = _('Guardian Profiles')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Guardian Profile for {self.user}'

    def clean(self) -> None:
        if self.user.role.name != RoleName.GUARDIAN:
            raise ValidationError(_("User must have role 'guardian' for GuardianProfile."))


class TeacherProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('User')
    )
    tsc_number = models.CharField(max_length=50, blank=True, verbose_name=_('TSC number'))
    id_number = models.CharField(max_length=20, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_('Phone number'))
    email = models.EmailField(blank=True, verbose_name=_('Email address'))
    status = models.CharField(
        max_length=20,
        choices=TeacherStatus.choices,
        default=TeacherStatus.ACTIVE,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'), )

    class Meta:
        verbose_name = _('Teacher Profile')
        verbose_name_plural = _('Teacher Profiles')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Profile for {self.user}'

    def clean(self) -> None:
        if self.user.role.name != RoleName.TEACHER:
            raise ValidationError(_("User must have role 'teacher' for TeacherProfile."))


class ClerkProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='clerk_profile',
        verbose_name=_('User')
    )
    id_number = models.CharField(max_length=20, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=12, blank=True, verbose_name=_('Phone number'))
    email = models.EmailField(blank=True, verbose_name=_('Email address'))
    status = models.CharField(
        max_length=20,
        choices=ClerkStatus.choices,
        default=ClerkStatus.ACTIVE,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'), )

    class Meta:
        verbose_name = _('Clerk Profile')
        verbose_name_plural = _('Clerk Profiles')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Profile for {self.user}'

    def clean(self) -> None:
        if self.user.role.name != RoleName.CLERK:
            raise ValidationError(_("User must have role 'clerk' for ClerkProfile."))


class AdminProfile(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name=_('User')
    )
    id_number = models.CharField(max_length=20, blank=True, verbose_name=_('ID number'))
    phone_number = models.CharField(max_length=12, blank=True, verbose_name=_('Phone number'))
    email = models.EmailField(blank=True, verbose_name=_('Email address'))
    status = models.CharField(
        max_length=20,
        choices=AdminStatus.choices,
        default=AdminStatus.ACTIVE,
        verbose_name=_('Status')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'), )

    class Meta:
        verbose_name = _('Admin Profile')
        verbose_name_plural = _('Admin Profiles')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Profile for {self.user}'

    def clean(self) -> None:
        if self.user.role.name != RoleName.ADMIN:
            raise ValidationError(_("User must have role 'admin' for AdminProfile."))


class Device(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(unique=True, max_length=255)
    last_activity = models.DateTimeField(blank=True, editable=False)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        status = 'Active' if self.is_active else 'Inactive'
        return f'{self.user.username} ({status})'

    class Meta(object):
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'token'], name='unique_user_token')
        ]
        indexes = [
            models.Index(fields=['token']),
        ]
