from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Identity


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'device',
        'status',
        'token',
        'expires_at',
        'source_ip',
        'created_at',
    )
    list_filter = (
        'status',
        'expires_at',
        'created_at',
    )
    search_fields = (
        'user__id',
        'user__username',
        'user__reg_number',
        'user__first_name',
        'user__last_name',
        'user__other_name',
        'device__token',
        'token',
        'source_ip',
    )
    readonly_fields =  AUDIT_READONLY_FIELDS + (
        'token',
        'expires_at',
        'source_ip'
    )
    ordering = ('-created_at',)

    fieldsets = (
        (_('User & Status'), {
            'fields': ('user', 'device', 'status')
        }),
        (_('Token Info'), {
            'fields': ('token', 'expires_at', 'source_ip')
        }),
        AUDIT_FIELDSET,
    )