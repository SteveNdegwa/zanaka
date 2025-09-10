from django.contrib import admin
from .models import School, Branch, Classroom


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'contact_email', 'contact_phone', 'established_date')
    search_fields = ('name', 'code', 'contact_email')
    list_filter = ('established_date',)
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description')
        }),
        ('Contact Information', {
            'fields': ('address', 'contact_email', 'contact_phone')
        }),
        ('Details', {
            'fields': ('established_date',)
        }),
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'school', 'location', 'principal', 'capacity', 'status',
        'established_date', 'date_created'
    )
    search_fields = ('name', 'school__name', 'location', 'principal__username')
    list_filter = ('status', 'school', 'established_date')
    raw_id_fields = ('principal',)
    fieldsets = (
        (None, {
            'fields': ('name', 'school', 'description')
        }),
        ('Details', {
            'fields': ('location', 'capacity', 'status', 'established_date')
        }),
        ('Contact', {
            'fields': ('contact_email', 'contact_phone', 'website')
        }),
        ('Management', {
            'fields': ('principal',)
        }),
    )


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'capacity')
    search_fields = ('name', 'branch__name', 'branch__school__name')
    list_filter = ('branch__school', 'branch')
    fieldsets = (
        (None, {
            'fields': ('name', 'branch', 'description')
        }),
        ('Capacity', {
            'fields': ('capacity',)
        }),
    )
