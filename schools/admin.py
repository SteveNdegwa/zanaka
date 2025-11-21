from django.contrib import admin

from .models import School, Branch, Classroom


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    fieldsets = (
        ('School Info', {
            'fields': ('name', 'code', 'address', 'contact_email', 'contact_phone', 'established_date', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at', 'synced')
        }),
    )

    list_display = ('name', 'code', 'contact_email', 'contact_phone', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at', 'synced')
    search_fields = ('id', 'name', 'code', 'contact_email', 'contact_phone')
    readonly_fields = ('id', 'created_at', 'updated_at', 'synced')
    ordering = ('name', '-created_at')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Branch Info', {
            'fields': ('name', 'school', 'location', 'contact_email', 'contact_phone', 'principal',
                       'capacity', 'established_date', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at', 'synced')
        }),
    )

    list_display = ('name', 'school', 'location', 'principal', 'capacity', 'is_active', 'created_at', 'updated_at')
    list_filter = ('school', 'principal', 'is_active', 'created_at', 'updated_at', 'synced')
    search_fields = (
        'id', 'name', 'school__id', 'school__name', 'location',
        'principal__id', 'principal__username', 'principal__first_name', 'principal__last_name'
    )
    raw_id_fields = ('school', 'principal')
    readonly_fields = ('id', 'created_at', 'updated_at', 'synced')
    ordering = ('name', '-created_at')


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Classroom Info', {
            'fields': ('name', 'branch', 'grade_level', 'capacity', 'is_active')
        }),
        ('Audit', {
            'fields': ('id', 'created_at', 'updated_at', 'synced')
        }),
    )

    list_display = ('name', 'branch', 'grade_level', 'capacity', 'is_active', 'created_at', 'updated_at')
    list_filter = ('branch', 'grade_level', 'is_active', 'created_at', 'updated_at', 'synced')
    search_fields = (
        'id', 'name', 'branch__id', 'branch__name',
        'branch__school__name', 'grade_level'
    )
    raw_id_fields = ('branch',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'synced')
    ordering = ('branch__name', 'name', '-created_at')
