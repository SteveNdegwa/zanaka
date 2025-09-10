from django.contrib import admin
from django.contrib.auth.models import Group

from .models import (
    Role,
    Permission,
    RolePermission,
    ExtendedPermission,
    User,
    StudentGuardian,
    StudentProfile,
    GuardianProfile,
    TeacherProfile,
    ClerkProfile,
    AdminProfile,
    Device,
)

admin.site.unregister(Group)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Role Info', {
            'fields': ('name', 'description', 'can_login', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('name', 'can_login', 'is_active', 'date_created', 'date_modified')
    list_filter = ('can_login', 'is_active', 'date_created', 'date_modified', 'synced')
    search_fields = ('id', 'name', 'description')
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Permission Info', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('name', 'is_active', 'date_created', 'date_modified')
    list_filter = ('is_active', 'date_created', 'date_modified', 'synced')
    search_fields = ('id', 'name', 'description')
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Role ↔ Permission Link', {
            'fields': ('role', 'permission', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('role', 'permission', 'is_active', 'date_created', 'date_modified')
    list_filter = ('role', 'permission', 'is_active', 'date_created', 'date_modified', 'synced')
    search_fields = ('id', 'role__id', 'role__name', 'permission__id', 'permission__name')
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(ExtendedPermission)
class ExtendedPermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Extended Permission', {
            'fields': ('user', 'permission', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'permission', 'is_active', 'date_created', 'date_modified')
    list_filter = ('permission', 'is_active', 'date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name',
        'user__last_name', 'permission__id', 'permission__name',
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Unique Identifiers', {
            'fields': ('id', 'username', 'reg_number')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'other_name', 'last_name', 'date_of_birth', 'gender')
        }),
        ('School Info', {
            'fields': ('role', 'branch')
        }),
        ('System Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Authentication', {
            'fields': ('password',)
        }),
        ('Activity', {
            'fields': ('last_activity',)
        }),
        ('Audit', {
            'fields': ('date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('username', 'full_name', 'role', 'branch', 'is_active', 'date_created', 'date_modified')
    list_filter = ('role', 'branch', 'is_active', 'is_staff', 'date_created', 'date_modified')
    search_fields = ('id', 'username', 'first_name', 'last_name', 'other_name', 'reg_number')
    readonly_fields = ('id', 'username', 'reg_number', 'date_created', 'date_modified', 'synced', 'last_activity')
    ordering = ('-date_created',)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Student Info', {
            'fields': ('user', 'classroom', 'knec_number', 'nemis_number')
        }),
        ('Additional Info', {
            'fields': ('medical_info', 'additional_info')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'classroom', 'knec_number', 'nemis_number', 'date_created', 'date_modified')
    list_filter = ('classroom', 'date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name',
        'user__last_name', 'user__other_name', 'knec_number', 'nemis_number'
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(GuardianProfile)
class GuardianProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Guardian Info', {
            'fields': ('user', 'id_number', 'phone_number', 'email', 'occupation')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'id_number', 'phone_number', 'email', 'occupation', 'date_created', 'date_modified')
    list_filter = ('date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name',
        'user__last_name', 'user__other_name', 'id_number', 'phone_number', 'email'
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Teacher Info', {
            'fields': ('user', 'tsc_number', 'id_number', 'phone_number', 'email')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'tsc_number', 'id_number', 'phone_number', 'email', 'date_created', 'date_modified')
    list_filter = ('date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name', 'user__last_name',
        'user__other_name', 'tsc_number', 'id_number', 'phone_number', 'email',
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(ClerkProfile)
class ClerkProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Clerk Info', {
            'fields': ('user', 'id_number', 'phone_number', 'email')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'id_number', 'phone_number', 'email', 'date_created', 'date_modified')
    list_filter = ('date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name', 'user__last_name',
        'user__other_name', 'id_number', 'phone_number', 'email'
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Admin Info', {
            'fields': ('user', 'id_number', 'phone_number', 'email')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'id_number', 'phone_number', 'email', 'date_created', 'date_modified')
    list_filter = ('date_created', 'date_modified', 'synced')
    search_fields = (
        'id', 'user__id', 'user__username', 'user__reg_number', 'user__first_name', 'user__last_name',
        'user__other_name', 'id_number', 'phone_number', 'email'
    )
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Student ↔ Guardian Link', {
            'fields': ('student', 'guardian', 'relationship', 'is_primary')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('student', 'guardian', 'relationship', 'is_primary', 'date_created', 'date_modified')
    list_filter = ('relationship', 'is_primary', 'date_created', 'date_modified', 'synced')
    search_fields = (
        'student__user__id', 'student__user__reg_number', 'student__user__username',
        'student__user__first_name', 'student__user__last_name', 'student__user__other_name',
        'guardian__id', 'guardian__username', 'guardian__reg_number', 'guardian__first_name',
        'guardian__last_name', 'guardian__other_name'
    )
    raw_id_fields = ('student', 'guardian')
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Device Info', {
            'fields': ('user', 'token', 'is_active')
        }),
        ('Activity', {
            'fields': ('last_activity',)
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
    list_display = ('user', 'token', 'is_active', 'last_activity', 'date_created', 'date_modified')
    list_filter = ('is_active', 'date_created', 'date_modified', 'synced')
    search_fields = (
        'token', 'user__username', 'user__id_number', 'user__phone_number',
        'user__email', 'user__first_name', 'user__last_name',
    )
    readonly_fields = ('id', 'last_activity', 'date_created', 'date_modified', 'synced')
    ordering = ('-date_created',)
