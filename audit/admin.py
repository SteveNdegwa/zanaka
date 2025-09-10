from django.contrib import admin

from audit.models import RequestLog, AuditLog, AuditConfiguration


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = (
        'request_id', 'user', 'request_method', 'request_path', 'activity_name', 'is_authenticated',
        'ip_address', 'started_at', 'ended_at', 'time_taken', 'response_status'
    )
    list_filter = (
        'is_authenticated', 'request_method', 'is_secure', 'activity_name', 'view_name',
        'response_status', 'started_at'
    )
    search_fields = (
        'request_id', 'user__username', 'token', 'ip_address', 'session_key',
        'request_path', 'activity_name', 'view_name', 'exception_type'
    )
    ordering = ('-started_at',)
    readonly_fields = (
        'request_id', 'started_at', 'ended_at', 'time_taken', 'response_status',
        'response_data', 'id', 'date_created', 'date_modified', 'synced'
    )
    fieldsets = (
        ('Request Info', {
            'fields': ('request_id', 'request_method', 'request_path', 'is_secure', 'user_agent')
        }),
        ('User & Session', {
            'fields': ('user', 'token', 'is_authenticated', 'ip_address', 'session_key')
        }),
        ('View & Activity', {
            'fields': ('view_name', 'view_args', 'view_kwargs', 'activity_name')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'time_taken')
        }),
        ('Response', {
            'fields': ('response_status', 'response_data')
        }),
        ('Exceptions', {
            'fields': ('exception_type', 'exception_message')
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('date_created', 'event_type', 'severity', 'object_repr', 'user', 'request_id', 'ip_address')
    list_filter = ('event_type', 'severity', 'date_created')
    search_fields = ('object_repr', 'object_id', 'user__username', 'request_id')
    readonly_fields = (
        'id', 'date_created', 'date_modified', 'synced',
        'request_id', 'user', 'ip_address', 'user_agent', 'request_method', 'request_path', 'activity_name',
        'content_type', 'object_id', 'object_repr'
    )

    fieldsets = (
        ('Request Information', {
            'fields': (
                'request_id', 'user', 'ip_address', 'user_agent', 'request_method', 'request_path', 'activity_name'
            )
        }),
        ('Event Information', {
            'fields': ('event_type', 'severity')
        }),
        ('Object Information', {
            'fields': ('content_type', 'object_id', 'object_repr')
        }),
        ('Change Information', {
            'fields': ('changes',)
        }),
        ('Additional Context', {
            'fields': ('metadata',)
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )


@admin.register(AuditConfiguration)
class AuditConfigurationAdmin(admin.ModelAdmin):
    list_display = ('app_label', 'model_name', 'is_enabled', 'track_create', 'track_update', 'track_delete')
    list_filter = ('is_enabled', 'track_create', 'track_update', 'track_delete')
    search_fields = ('app_label', 'model_name')
    readonly_fields = ('id', 'date_created', 'date_modified', 'synced')
    fieldsets = (
        ('Model Information', {
            'fields': ('app_label', 'model_name')
        }),
        ('Tracking Options', {
            'fields': ('is_enabled', 'track_create', 'track_update', 'track_delete', 'excluded_fields')
        }),
        ('Retention', {
            'fields': ('retention_days',)
        }),
        ('Audit', {
            'fields': ('id', 'date_created', 'date_modified', 'synced')
        }),
    )
