import base64
import re

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from .models import (
    Role, Permission, RolePermission, ExtendedPermission,
    User, StudentProfile, GuardianProfile, TeacherProfile,
    ClerkProfile, AdminProfile, StudentGuardian,
    StudentClassroomAssignment, StudentClassroomMovement, Device,
    RoleName, StudentType,
)


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'colored_can_login', 'is_active')
    list_filter = ('can_login', 'is_active')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': ('name', 'can_login', 'is_active'),
        }),
        AUDIT_FIELDSET,
    )

    def colored_can_login(self, obj):
        color = 'green' if obj.can_login else 'gray'
        text = _('Yes') if obj.can_login else _('No')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, text
        )
    colored_can_login.short_description = _('Can Login')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active'),
        }),
        AUDIT_FIELDSET,
    )


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    verbose_name = _('Permission')
    verbose_name_plural = _('Permissions')


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('role__name', 'permission__name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': ('role', 'permission', 'is_active'),
        }),
        AUDIT_FIELDSET,
    )


class ExtendedPermissionInline(admin.TabularInline):
    model = ExtendedPermission
    extra = 1
    verbose_name = _('Extended Permission')
    verbose_name_plural = _('Extended Permissions')


@admin.register(ExtendedPermission)
class ExtendedPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission', 'is_active')
    list_filter = ('is_active', 'permission')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'permission__name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': ('user', 'permission', 'is_active'),
        }),
        AUDIT_FIELDSET,
    )


class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0
    readonly_fields = ('token', 'last_activity')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_preview', 'last_activity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'token')
    readonly_fields = AUDIT_READONLY_FIELDS + ('token', 'last_activity')

    fieldsets = (
        (None, {
            'fields': ('user', 'token', 'is_active'),
        }),
        (_('Activity'), {
            'fields': ('last_activity',),
            'classes': ('collapse',),
        }),
        AUDIT_FIELDSET,
    )

    def token_preview(self, obj):
        return (obj.token[:30] + '...') if obj.token and len(obj.token) > 30 else (obj.token or '—')
    token_preview.short_description = _('Token')


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ('student', 'guardian', 'relationship', 'is_primary', 'can_receive_reports', 'is_active')
    list_filter = ('relationship', 'is_primary', 'can_receive_reports', 'is_active')
    search_fields = (
        'student__first_name', 'student__last_name',
        'guardian__first_name', 'guardian__last_name',
    )
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': (
                'student', 'guardian', 'relationship',
                'is_primary', 'can_receive_reports', 'is_active',
            ),
        }),
        AUDIT_FIELDSET,
    )


class StudentClassroomAssignmentInline(admin.TabularInline):
    model = StudentClassroomAssignment
    extra = 0
    readonly_fields = ('classroom', 'academic_year', 'is_current')


@admin.register(StudentClassroomAssignment)
class StudentClassroomAssignmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'academic_year', 'is_current')
    list_filter = ('academic_year', 'is_current', 'classroom')
    search_fields = ('student__first_name', 'student__last_name', 'classroom__name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': ('student', 'classroom', 'academic_year', 'is_current'),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(StudentClassroomMovement)
class StudentClassroomMovementAdmin(admin.ModelAdmin):
    list_display = ('student', 'movement_type', 'from_classroom', 'to_classroom', 'academic_year', 'performed_by')
    list_filter = ('movement_type', 'academic_year')
    search_fields = ('student__first_name', 'student__last_name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (None, {
            'fields': (
                'student', 'from_classroom', 'to_classroom',
                'academic_year', 'movement_type', 'reason', 'performed_by',
            ),
        }),
        AUDIT_FIELDSET,
    )


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = _('Student Profile')

    fieldsets = (
        (_('Student Details'), {
            'fields': ('student_type', 'knec_number', 'nemis_number'),
        }),
        (_('Subscriptions'), {
            'fields': ('subscribed_to_transport', 'subscribed_to_meals'),
        }),
        (_('Additional Information'), {
            'fields': ('admission_date', 'medical_info', 'additional_info'),
            'classes': ('collapse',),
        }),
        (_('Status'), {
            'fields': ('status', 'is_active'),
        }),
    )


class GuardianProfileInline(admin.StackedInline):
    model = GuardianProfile
    can_delete = False
    verbose_name_plural = _('Guardian Profile')

    fieldsets = (
        (_('Contact & Identification'), {
            'fields': ('id_number', 'phone_number', 'email'),
        }),
        (_('Other'), {
            'fields': ('occupation', 'status', 'is_active'),
        }),
    )


class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    verbose_name_plural = _('Teacher Profile')

    fieldsets = (
        (_('Professional Details'), {
            'fields': ('tsc_number', 'id_number'),
        }),
        (_('Contact'), {
            'fields': ('phone_number', 'email'),
        }),
        (_('Status'), {
            'fields': ('status', 'is_active'),
        }),
    )


class ClerkProfileInline(admin.StackedInline):
    model = ClerkProfile
    can_delete = False
    verbose_name_plural = _('Clerk Profile')

    fieldsets = (
        (_('Contact & Identification'), {
            'fields': ('id_number', 'phone_number', 'email'),
        }),
        (_('Status'), {
            'fields': ('status', 'is_active'),
        }),
    )


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = _('Admin Profile')

    fieldsets = (
        (_('Contact & Identification'), {
            'fields': ('id_number', 'phone_number', 'email'),
        }),
        (_('Status'), {
            'fields': ('status', 'is_active'),
        }),
    )


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    fk_name = 'student'                  # Links to the student (ForeignKey)
    extra = 1
    verbose_name = _('Guardian')
    verbose_name_plural = _('Guardians')
    fields = ('guardian', 'relationship', 'is_primary', 'can_receive_reports', 'is_active')
    autocomplete_fields = ('guardian',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('guardian', 'guardian__role')


class GuardianStudentInline(admin.TabularInline):
    model = StudentGuardian
    fk_name = 'guardian'                 # Links to the guardian (ForeignKey)
    extra = 1
    verbose_name = _('Student')
    verbose_name_plural = _('Students')
    fields = ('student', 'relationship', 'is_primary', 'can_receive_reports', 'is_active')
    autocomplete_fields = ('student',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'student__role')


def reset_user_password(modeladmin, request, queryset):
    count = 0
    for user in queryset:
        if user.role.can_login:
            user.reset_password()
            count += 1
    modeladmin.message_user(request, _(f"Password reset sent to {count} user(s)."))


reset_user_password.short_description = _("Reset password & send via email")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'photo_thumbnail',
        'username', 'reg_number', 'full_name_link', 'colored_role',
        'school', 'colored_account_status', 'colored_profile_status',
        'force_pass_reset', 'last_activity',
    )
    list_filter = (
        'role__name', 'school', 'branches', 'gender', 'is_active', 'is_superuser',
        'force_pass_reset',
    )
    search_fields = (
        'id', 'username', 'reg_number', 'first_name', 'last_name', 'other_name',
        'town_of_residence', 'county_of_residence',
    )
    readonly_fields = AUDIT_READONLY_FIELDS + (
        'username', 'reg_number', 'last_activity',
        'branch_info_display', 'photo_preview'  # photo_preview is readonly
    )
    actions = [reset_user_password]
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    inlines = [ExtendedPermissionInline, DeviceInline]

    def get_inlines(self, request, obj=None):
        inlines = [ExtendedPermissionInline, DeviceInline]
        if obj:
            role = obj.role.name
            if role == RoleName.STUDENT:
                inlines = [
                              StudentProfileInline,
                              StudentClassroomAssignmentInline,
                              StudentGuardianInline
                          ] + inlines
            elif role == RoleName.GUARDIAN:
                inlines = [
                              GuardianProfileInline,
                              GuardianStudentInline,
                          ] + inlines
            elif role == RoleName.TEACHER:
                inlines = [TeacherProfileInline] + inlines
            elif role == RoleName.CLERK:
                inlines = [ClerkProfileInline] + inlines
            elif role == RoleName.ADMIN:
                inlines = [AdminProfileInline] + inlines
        return inlines

    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            (None, {
                'fields': ('username', 'reg_number', 'role', 'school', 'branch_info_display', 'branches'),
            }),
            (_('Personal Information'), {
                'fields': (
                    ('first_name', 'other_name', 'last_name'),
                    ('date_of_birth', 'gender'),
                    'photo',
                    'photo_preview',
                ),
            }),
            (_('Residence Information'), {
                'fields': ('town_of_residence', 'county_of_residence', 'address'),
                'classes': ('collapse',),
            }),
            (_('Last Activity'), {
                'fields': ('last_activity',),
                'classes': ('collapse',),
            }),
            (_('Account Status'), {
                'fields': ('is_active', 'is_staff', 'force_pass_reset'),
            }),
            AUDIT_FIELDSET,
        )
        return fieldsets

    @staticmethod
    def _get_clean_base64(obj):
        if not obj.photo:
            return None

        data = str(obj.photo).strip()

        # If it has the data URI prefix, extract the base64 part
        if data.startswith('data:image'):
            match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)', data)
            if match:
                data = match.group(1)

        # Remove any whitespace/newlines
        data = re.sub(r'\s+', '', data)

        try:
            base64.b64decode(data, validate=True)
            return data
        except Exception:
            return None

    def photo_thumbnail(self, obj):
        clean_b64 = self._get_clean_base64(obj)
        if not clean_b64:
            return format_html(
                '<div style="width:40px; height:40px; background:#e2e8f0; border-radius:50%; '
                'display:flex; align-items:center; justify-content:center; font-size:18px; color:#718096;">'
                '👤'
                '</div>'
            )

        return format_html(
            '<img src="data:image/jpeg;base64,{}" '
            'style="width:40px; height:40px; object-fit:cover; border-radius:50%; border:2px solid #ddd;" '
            'alt="Profile photo" />',
            clean_b64
        )

    photo_thumbnail.short_description = "Photo"

    def photo_preview(self, obj):
        clean_b64 = self._get_clean_base64(obj)
        if not clean_b64:
            return "No photo uploaded or invalid data"

        return format_html(
            '<div style="text-align:center; margin:20px 0;">'
            '<img src="data:image/jpeg;base64,{}" '
            'style="max-width:350px; max-height:350px; border-radius:12px; '
            'box-shadow:0 4px 12px rgba(0,0,0,0.15); object-fit:contain; background:#f8f9fa;" '
            'alt="Profile photo" />'
            '<p style="margin-top:12px; color:#666; font-style:italic;">'
            'Current profile photo'
            '</p>'
            '</div>',
            clean_b64
        )

    photo_preview.short_description = "Photo Preview"

    def full_name_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse('admin:users_user_change', args=[obj.pk])
        return format_html('<a href="{}"><b>{}</b></a>', url, obj.full_name or obj.username)

    full_name_link.short_description = _('Full Name')

    def colored_role(self, obj):
        colors = {
            RoleName.STUDENT: 'dodgerblue',
            RoleName.GUARDIAN: 'mediumseagreen',
            RoleName.TEACHER: 'purple',
            RoleName.CLERK: 'orange',
            RoleName.ADMIN: 'crimson',
        }
        color = colors.get(obj.role.name if obj.role else None, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.role.name.title() if obj.role else '—'
        )

    colored_role.short_description = _('Role')

    def colored_account_status(self, obj):
        if not obj.is_active:
            color, text = 'darkred', _('Inactive')
        elif obj.force_pass_reset:
            color, text = 'orange', _('Password Reset Required')
        else:
            color, text = 'green', _('Active')
        return format_html(
            '<b style="color:white; background:{}; padding:2px 8px; border-radius:4px;">{}</b>',
            color, text
        )

    colored_account_status.short_description = _('Account')

    def colored_profile_status(self, obj):
        profile = None
        if obj.role.name == RoleName.STUDENT and hasattr(obj, 'student_profile'):
            profile = obj.student_profile
        elif obj.role.name == RoleName.GUARDIAN and hasattr(obj, 'guardian_profile'):
            profile = obj.guardian_profile
        elif obj.role.name == RoleName.TEACHER and hasattr(obj, 'teacher_profile'):
            profile = obj.teacher_profile
        elif obj.role.name == RoleName.CLERK and hasattr(obj, 'clerk_profile'):
            profile = obj.clerk_profile
        elif obj.role.name == RoleName.ADMIN and hasattr(obj, 'admin_profile'):
            profile = obj.admin_profile

        if not profile:
            return "—"

        status = profile.status
        colors = {
            'ACTIVE': 'green',
            'SUSPENDED': 'red',
            'GRADUATED': 'dodgerblue',
            'TRANSFERRED': 'purple',
            'RETIRED': 'gray',
            'TERMINATED': 'black',
            'ON_LEAVE': 'orange',
        }
        color = colors.get(status, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, profile.get_status_display()
        )

    colored_profile_status.short_description = _('Profile Status')

    def branch_info_display(self, obj):
        if not obj or not obj.school:
            return format_html('<span style="color:gray;">{}</span>', _('No school assigned'))

        branches = obj.effective_branches
        count = branches.count()

        if count == 0:
            return format_html('<span style="color:orange;">{}</span>', _('No active branch association'))

        is_full_access = (
                obj.role.name in [RoleName.ADMIN, RoleName.CLERK, RoleName.TEACHER] and
                not obj.branches.exists() and
                obj.school.branches.filter(is_active=True).count() == count
        )

        if is_full_access:
            return format_html(
                '<span style="color:white; background:#28a745; padding:8px 14px; border-radius:8px; '
                'font-weight:bold; font-size:1.1em; display:inline-block;">'
                '🌐 {} ({})'
                '</span>',
                _('All Branches Access'),
                count
            )

        branch_list = list(branches.values_list('name', flat=True))
        full_list = "<br>".join(branch_list)

        if count == 1:
            color = '#007bff'  # Blue
            icon = '📍'
            text = branch_list[0]
        else:
            color = '#343a40'  # Dark gray
            icon = '🏫'
            text = f"{branch_list[0]} <small>(+{count - 1} more)</small>"

        return format_html(
            '<div style="line-height:1.6;">'
            '<span style="color:white; background:{}; padding:8px 14px; border-radius:8px; '
            'font-weight:bold; font-size:1.1em; display:inline-block;" '
            'title="{}">'
            '{} {}'
            '</span>'
            '<br><small style="color:#666; margin-top:6px; display:block;">{} {}</small>'
            '</div>',
            color,
            full_list,
            icon, text,
            _('Associated with'),
            count if count > 1 else _('branch')
        )

    branch_info_display.short_description = _('Branch Association')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_type_colored', 'status_colored', 'subscribed_to_transport', 'subscribed_to_meals')
    list_filter = ('student_type', 'status', 'subscribed_to_transport', 'subscribed_to_meals', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'knec_number', 'nemis_number')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Basic Info'), {
            'fields': ('user', 'student_type', 'knec_number', 'nemis_number'),
        }),
        (_('Subscriptions'), {
            'fields': ('subscribed_to_transport', 'subscribed_to_meals'),
        }),
        (_('Additional Info'), {
            'fields': ('admission_date', 'medical_info', 'additional_info'),
            'classes': ('collapse',),
        }),
        (_('Status'), {
            'fields': ('status', 'is_active'),
        }),
        AUDIT_FIELDSET,
    )

    def student_type_colored(self, obj):
        color = 'dodgerblue' if obj.student_type == StudentType.DAY_SCHOLAR else 'mediumseagreen'
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_student_type_display()
        )
    student_type_colored.short_description = _('Student Type')

    def status_colored(self, obj):
        colors = {'ACTIVE': 'green', 'SUSPENDED': 'red', 'GRADUATED': 'dodgerblue', 'TRANSFERRED': 'purple'}
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = _('Status')


@admin.register(GuardianProfile)
class GuardianProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_colored')
    list_filter = ('status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'id_number', 'phone_number')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Contact & ID'), {'fields': ('id_number', 'phone_number', 'email')}),
        (_('Other'), {'fields': ('occupation', 'status', 'is_active')}),
        AUDIT_FIELDSET,
    )

    def status_colored(self, obj):
        return format_html(
            '<span style="color:white; background:green; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            obj.get_status_display()
        )
    status_colored.short_description = _('Status')


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tsc_number', 'status_colored')
    list_filter = ('status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'tsc_number')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Professional'), {'fields': ('tsc_number', 'id_number')}),
        (_('Contact'), {'fields': ('phone_number', 'email')}),
        (_('Status'), {'fields': ('status', 'is_active')}),
        AUDIT_FIELDSET,
    )

    def status_colored(self, obj):
        colors = {
            'ACTIVE': 'green', 'SUSPENDED': 'red', 'RETIRED': 'gray',
            'TERMINATED': 'black', 'ON_LEAVE': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = _('Status')


@admin.register(ClerkProfile)
class ClerkProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_colored')
    list_filter = ('status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'id_number')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Contact & ID'), {'fields': ('id_number', 'phone_number', 'email')}),
        (_('Status'), {'fields': ('status', 'is_active')}),
        AUDIT_FIELDSET,
    )

    def status_colored(self, obj):
        colors = {'ACTIVE': 'green', 'TERMINATED': 'black', 'ON_LEAVE': 'orange'}
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = _('Status')


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_colored')
    list_filter = ('status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Contact & ID'), {'fields': ('id_number', 'phone_number', 'email')}),
        (_('Status'), {'fields': ('status', 'is_active')}),
        AUDIT_FIELDSET,
    )

    def status_colored(self, obj):
        colors = {'ACTIVE': 'green', 'TERMINATED': 'black', 'ON_LEAVE': 'orange'}
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = _('Status')