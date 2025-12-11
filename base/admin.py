from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.forms import Textarea

from .models import SystemSettings


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'system_name',
        'two_factor_authentication_required',
        'api_key_verification_required',
        'signature_verification_required',
        'send_notifications_async',
        'created_at',
        'updated_at',
    )
    search_fields = ('system_name',)
    ordering = ('-created_at',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('System'), {
            'fields': ('system_name',)
        }),
        (_('Authentication'), {
            'fields': (
                'cookie_secure',
                'auth_token_cookie_name',
                'auth_token_validity_seconds',
                'auth_token_allow_header_fallback',
                'two_factor_authentication_required',
            )
        }),
        (_('OTP'), {
            'fields': (
                'otp_length',
                'otp_validity_seconds',
                'action_otp_validity_seconds',
                'max_otp_attempts',
            )
        }),
        (_('API Gateway'), {
            'fields': (
                'encrypted_header',
                'api_key_header',
                'api_key_verification_required',
                'api_key_verification_exempt_paths',
                'signature_verification_required',
                'csrf_exempt_paths',
                'save_request_log_exempt_paths',
            )
        }),
        (_('Notifications'), {
            'fields': ('send_notifications_async',)
        }),
        AUDIT_FIELDSET,
    )

    formfield_overrides = {
        SystemSettings._meta.get_field('api_key_verification_exempt_paths'): {
            'widget': Textarea(attrs={'rows': 4, 'cols': 60})
        },
        SystemSettings._meta.get_field('csrf_exempt_paths'): {
            'widget': Textarea(attrs={'rows': 4, 'cols': 60})
        },
        SystemSettings._meta.get_field('save_request_log_exempt_paths'): {
            'widget': Textarea(attrs={'rows': 4, 'cols': 60})
        },
    }

    def has_add_permission(self, request):
        if SystemSettings.objects.exists():
            return False
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        if not change and SystemSettings.objects.exists():
            raise ValidationError(_('Only one SystemSettings instance is allowed.'))
        super().save_model(request, obj, form, change)