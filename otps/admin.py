from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OTP, OTPPurpose


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_link',
        'contact',
        'colored_purpose',
        'delivery_method',
        'colored_status',
        'retry_count',
        'expires_at',
        'created_at',
    )
    list_filter = (
        'purpose',
        'delivery_method',
        'is_used',
        'created_at',
        'expires_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'contact',
        'code',
    )
    readonly_fields = AUDIT_READONLY_FIELDS + (
        'code',
        'is_used',
        'retry_count',
        'expires_at',
        'is_valid',
        'is_expired',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fieldsets = (
        (_('Recipient'), {
            'fields': ('user', 'identity', 'contact'),
        }),
        (_('OTP Details'), {
            'fields': ('purpose', 'delivery_method', 'code', 'expires_at'),
        }),
        (_('Status & Attempts'), {
            'fields': ('is_used', 'retry_count', 'is_valid', 'is_expired'),
        }),
        AUDIT_FIELDSET,
    )

    def user_link(self, obj):
        if not obj.user:
            return "—"
        url = f"/cia/users/user/{obj.user.id}/change/"
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.full_name or obj.user.username
        )
    user_link.short_description = _('User')

    def colored_purpose(self, obj):
        colors = {
            OTPPurpose.PHONE_VERIFICATION: 'dodgerblue',
            OTPPurpose.EMAIL_VERIFICATION: 'mediumseagreen',
            OTPPurpose.TWO_FACTOR_AUTHENTICATION: 'purple',
            OTPPurpose.PASSWORD_RESET: 'crimson',
        }
        color = colors.get(obj.purpose, 'gray')
        return format_html(
            '<span style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color,
            obj.get_purpose_display()
        )
    colored_purpose.short_description = _('Purpose')

    def colored_status(self, obj):
        if obj.is_used:
            color, text = 'green', _('Used')
        elif obj.is_expired:
            color, text = 'darkred', _('Expired')
        elif obj.retry_count >= 3:
            color, text = 'orange', _('Too Many Attempts')
        else:
            color, text = 'blue', _('Active')

        return format_html(
            '<b style="color:white; background:{}; padding:2px 8px; border-radius:4px; font-weight:bold;">{}</b>',
            color,
            text
        )
    colored_status.short_description = _('Status')

    def is_valid(self, obj):
        return obj.is_valid
    is_valid.boolean = True
    is_valid.short_description = _('Is Valid')

    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = _('Is Expired')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser