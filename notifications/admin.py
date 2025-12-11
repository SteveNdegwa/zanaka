from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Template, Provider, Notification


AUDIT_FIELDSET = (_('Audit'), {
    'fields': ('id', 'created_at', 'updated_at', 'synced'),
    'classes': ('collapse',)
})

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'notification_type', 'subject_preview', 'is_active', 'created_at')
    list_filter = ('notification_type', 'is_active', 'created_at')
    search_fields = ('name', 'subject', 'body')
    ordering = ('-created_at',)

    fieldsets = (
        (_('Template Details'), {
            'fields': ('name', 'notification_type', 'subject', 'body')
        }),
        (_('Status'), {
            'fields': ('is_active',),
        }),
        AUDIT_FIELDSET,
    )
    readonly_fields = AUDIT_READONLY_FIELDS

    def subject_preview(self, obj):
        return (obj.subject[:50] + '...') if len(obj.subject) > 50 else obj.subject
    subject_preview.short_description = _('Subject')


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'notification_type', 'priority', 'class_name', 'is_active', 'created_at')
    list_filter = ('notification_type', 'is_active', 'created_at')
    search_fields = ('name', 'class_name')
    ordering = ('priority', 'name')

    fieldsets = (
        (_('Provider Details'), {
            'fields': ('name', 'notification_type', 'priority', 'class_name')
        }),
        (_('Configuration'), {
            'fields': ('config',),
            'description': _('JSON configuration for the provider (API keys, endpoints, etc.)')
        }),
        (_('Status'), {
            'fields': ('is_active',),
        }),
        AUDIT_FIELDSET,
    )
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'colored_type',
        'colored_status',
        'provider',
        'recipient_preview',
        'frequency',
        'sent_time',
        'created_at'
    )
    list_filter = (
        'notification_type',
        'status',
        'frequency',
        'provider',
        'created_at',
        'sent_time'
    )
    search_fields = (
        'unique_key',
        'recipients',
        'user__username',
        'user__first_name',
        'user__last_name',
        'failure_message'
    )
    readonly_fields = AUDIT_READONLY_FIELDS + ('sent_time', 'failure_traceback')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        (_('Recipient & Type'), {
            'fields': ('user', 'notification_type', 'template', 'provider', 'recipients')
        }),
        (_('Content & Context'), {
            'fields': ('context', 'frequency', 'unique_key'),
            'classes': ('collapse',)
        }),
        (_('Delivery Status'), {
            'fields': ('status', 'sent_time', 'failure_message', 'failure_traceback'),
        }),
        AUDIT_FIELDSET,
    )

    # Colored badges
    def colored_type(self, obj):
        colors = {'EMAIL': 'blue', 'SMS': 'green'}
        color = colors.get(obj.notification_type, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_notification_type_display()
        )
    colored_type.short_description = _('Type')

    def colored_status(self, obj):
        colors = {
            'PENDING': 'orange',
            'QUEUED': 'purple',
            'CONFIRMATION_PENDING': 'goldenrod',
            'SENT': 'green',
            'FAILED': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color:white; background-color:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )

    def recipient_preview(self, obj):
        # noinspection PyBroadException
        try:
            if obj.recipients and isinstance(obj.recipients, (list, tuple)):
                first = obj.recipients[0]
                extra = f" +{len(obj.recipients)-1}" if len(obj.recipients) > 1 else ""
                return f"{first}{extra}"
            return "—"
        except Exception:
            return _('Invalid')
    recipient_preview.short_description = _('Recipients')