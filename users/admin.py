from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import (
    User,
    Role,
    Permission,
    RolePermission,
    ExtendedPermission,
    StudentProfile,
    GuardianProfile,
    TeacherProfile,
    ClerkProfile,
    AdminProfile,
    StudentGuardian,
    Device
)


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    fields = ('knec_number', 'nemis_number', 'classroom', 'medical_info', 'additional_info')
    readonly_fields = ('knec_number', 'nemis_number')


class GuardianProfileInline(admin.StackedInline):
    model = GuardianProfile
    can_delete = False
    fields = ('id_number', 'phone_number', 'email', 'occupation')


class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    fields = ('tsc_number', 'id_number', 'phone_number', 'email')


class ClerkProfileInline(admin.StackedInline):
    model = ClerkProfile
    can_delete = False
    fields = ('id_number', 'phone_number', 'email')


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    fields = ('id_number', 'phone_number', 'email')


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    fk_name = 'student'
    extra = 1
    fields = ('guardian', 'relationship', 'is_primary', 'can_receive_reports', 'is_active')
    raw_id_fields = ('guardian',)



class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0
    fields = ('token', 'last_activity', 'is_active')
    readonly_fields = ('token', 'last_activity')


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
    list_display = ('name', 'can_login', 'is_active', 'created_at')
    list_filter = ('can_login', 'is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Role Details'), {
            'fields': ('name', 'can_login', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Permission'), {
            'fields': ('name', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'is_active')
    list_filter = ('role', 'permission', 'is_active')
    search_fields = ('role__name', 'permission__name')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Assignment'), {
            'fields': ('role', 'permission', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(ExtendedPermission)
class ExtendedPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'permission', 'is_active')
    list_filter = ('permission', 'is_active')
    search_fields = ('user__username', 'user__reg_number', 'permission__name')
    raw_id_fields = ('user',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Extended Permission'), {
            'fields': ('user', 'permission', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'reg_number',
        'full_name_display',
        'role',
        'branch',
        'is_staff',
        'is_active',
        'last_activity',
        'force_pass_reset',
    )
    list_filter = (
        'role',
        'branch__school',
        'branch',
        'is_staff',
        'is_active',
        'force_pass_reset',
        'last_activity',
        'created_at',
    )
    search_fields = (
        'id',
        'username',
        'reg_number',
        'first_name',
        'last_name',
        'other_name',
        'student_profile__knec_number',
        'student_profile__nemis_number',
        'student_profile__classroom__name',
        'guardian_profile__phone_number',
        'guardian_profile__email',
        'guardian_profile__id_number',
        'teacher_profile__phone_number',
        'teacher_profile__email',
        'teacher_profile__id_number',
        'teacher_profile__tsc_number',
        'clerk_profile__phone_number',
        'clerk_profile__email',
        'clerk_profile__id_number',
        'admin_profile__phone_number',
        'admin_profile__email',
        'admin_profile__id_number',
    )
    readonly_fields =  AUDIT_READONLY_FIELDS + (
        'username',
        'reg_number',
        'last_activity',
    )
    ordering = ('-created_at',)

    fieldsets = (
        (_('Account'), {
            'fields': ('username', 'password')
        }),
        (_('Personal Info'), {
            'fields': (
                'first_name',
                'last_name',
                'other_name',
                'date_of_birth',
                'gender',
                'reg_number',
            )
        }),
        (_('Role & Access'), {
            'fields': ('role', 'branch', 'is_staff', 'is_active', 'force_pass_reset')
        }),
        (_('Activity'), {
            'fields': ('last_activity',)
        }),
        AUDIT_FIELDSET,
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'first_name',
                'last_name',
                'other_name',
                'role',
                'branch',
                'is_staff',
                'is_active',
            ),
        }),
    )

    inlines = (
        StudentProfileInline,
        GuardianProfileInline,
        TeacherProfileInline,
        ClerkProfileInline,
        AdminProfileInline,
        StudentGuardianInline,
        DeviceInline,
    )

    def full_name_display(self, obj):
        return obj.full_name or '-'
    full_name_display.short_description = _('Full Name')

    def get_inlines(self, request, obj=None):
        if not obj:
            return []
        inlines = []
        if obj.role.name == 'STUDENT':
            inlines.append(StudentProfileInline)
            inlines.append(StudentGuardianInline)
        elif obj.role.name == 'GUARDIAN':
            inlines.append(GuardianProfileInline)
        elif obj.role.name == 'TEACHER':
            inlines.append(TeacherProfileInline)
        elif obj.role.name == 'CLERK':
            inlines.append(ClerkProfileInline)
        elif obj.role.name == 'ADMIN':
            inlines.append(AdminProfileInline)
        inlines.append(DeviceInline)
        return inlines

    def reset_user_password(self, request, obj):
        if not obj.role.can_login:
            self.message_user(request, f'User {obj} cannot login. Password not reset.', messages.WARNING)
            return
        try:
            obj.reset_password()
            self.message_user(request, f'Password reset successfully for {obj}. Email sent.', messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f'Failed to reset password: {e}', messages.ERROR)

    def reset_password_action(self, request, queryset):
        for user in queryset:
            self.reset_user_password(request, user)
    reset_password_action.short_description = _('Reset password & send email')

    actions = [reset_password_action]


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ('student', 'guardian', 'relationship', 'is_primary', 'can_receive_reports', 'is_active')
    list_filter = ('relationship', 'is_primary', 'can_receive_reports', 'is_active')
    search_fields = (
        'student__username',
        'student__reg_number',
        'guardian__username',
        'guardian__reg_number',
    )
    raw_id_fields = ('student', 'guardian')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Relationship'), {
            'fields': ('student', 'guardian', 'relationship', 'is_primary', 'can_receive_reports')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_preview', 'last_activity', 'is_active')
    list_filter = ('is_active', 'last_activity')
    search_fields = ('user__username', 'user__reg_number', 'token')
    readonly_fields = AUDIT_READONLY_FIELDS + ('token', 'last_activity')

    fieldsets = (
        (_('Device Info'), {
            'fields': ('user', 'token', 'last_activity', 'is_active')
        }),
        AUDIT_FIELDSET,
    )

    def token_preview(self, obj):
        return format_html(
            '<code style="font-size:90%;">{}</code>',
            obj.token[:40] + "..." if len(obj.token) > 40 else obj.token
        )

    token_preview.short_description = _('Token')
