from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from api.models import (
    ApiClient,
    ApiClientKey,
    SystemKey,
    APICallback,
    RateLimitRule,
    RateLimitAttempt,
    RateLimitBlock,
)


class ApiClientKeyInline(admin.TabularInline):
    model = ApiClientKey
    extra = 0
    readonly_fields = ('fingerprint', 'created_at', 'updated_at')
    fields = (
        'public_key',
        'fingerprint',
        'is_active',
        'expires_at',
        'created_at',
        'updated_at',
    )


class ApiCallbackInline(admin.TabularInline):
    model = APICallback
    extra = 0
    fields = ('path', 'require_authentication', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(ApiClient)
class ApiClientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'api_key',
        'signature_algorithm',
        'signature_header_key',
        'require_signature_verification',
        'is_active',
        'created_at',
    )
    search_fields = ('name', 'api_key')
    list_filter = (
        'is_active',
        'signature_algorithm',
        'require_signature_verification',
    )
    readonly_fields = AUDIT_READONLY_FIELDS + ('api_key',)
    inlines = (ApiClientKeyInline, ApiCallbackInline)

    fieldsets = (
        (_('Basic Info'), {
            'fields': ('name', 'is_active'),
        }),
        (_('API Settings'), {
            'fields': ('api_key', 'allowed_ips', 'meta'),
        }),
        (_('Signature Configuration'), {
            'fields': (
                'signature_algorithm',
                'signature_secret',
                'signature_header_key',
                'require_signature_verification',
            ),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(ApiClientKey)
class ApiClientKeyAdmin(admin.ModelAdmin):
    list_display = ('client', 'fingerprint', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('fingerprint', 'client__name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Key Info'), {
            'fields': ('client', 'public_key', 'fingerprint', 'is_active'),
        }),
        (_('Validity'), {
            'fields': ('expires_at',),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(SystemKey)
class SystemKeyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'fingerprint',
        'is_active',
        'expires_at',
        'created_at',
        'updated_at',
    )
    search_fields = ('name', 'fingerprint')
    list_filter = ('is_active',)
    readonly_fields = AUDIT_READONLY_FIELDS + ('fingerprint',)

    fieldsets = (
        (_('Key Info'), {
            'fields': (
                'name',
                'public_key',
                'private_key',
                'fingerprint',
            ),
        }),
        (_('Status'), {
            'fields': ('is_active', 'expires_at'),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(APICallback)
class APICallbackAdmin(admin.ModelAdmin):
    list_display = ('client', 'path', 'require_authentication', 'is_active', 'created_at')
    list_filter = ('client', 'require_authentication', 'is_active')
    search_fields = ('path', 'client__name')
    readonly_fields = AUDIT_READONLY_FIELDS
    ordering = ('client__name', 'path')

    fieldsets = (
        (_('Callback Info'), {
            'fields': ('client', 'path', 'is_active'),
        }),
        (_('Security'), {
            'fields': ('require_authentication',),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(RateLimitRule)
class RateLimitRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'scope',
        'limit',
        'period_count',
        'period',
        'is_active',
        'priority',
        'block_duration_minutes',
        'created_at',
    )
    list_filter = ('scope', 'period', 'is_active', 'created_at')
    search_fields = ('name', 'endpoint_pattern', 'http_methods')
    readonly_fields = AUDIT_READONLY_FIELDS
    ordering = ('-priority', 'name')

    fieldsets = (
        (_('General'), {
            'fields': ('name', 'scope', 'is_active', 'priority'),
        }),
        (_('Limits'), {
            'fields': ('limit', 'period_count', 'period', 'block_duration_minutes'),
        }),
        (_('Targeting'), {
            'fields': ('endpoint_pattern', 'http_methods'),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(RateLimitAttempt)
class RateLimitAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'rule',
        'key',
        'endpoint',
        'method',
        'count',
        'window_start',
        'last_attempt',
    )
    list_filter = ('rule', 'method', 'window_start')
    search_fields = ('key', 'endpoint', 'rule__name')
    readonly_fields = AUDIT_READONLY_FIELDS + ('last_attempt',)
    ordering = ('-last_attempt',)

    fieldsets = (
        (_('Rule & Target'), {
            'fields': ('rule', 'key', 'endpoint', 'method'),
        }),
        (_('Attempt Info'), {
            'fields': ('count', 'window_start', 'last_attempt'),
        }),
        AUDIT_FIELDSET,
    )


@admin.register(RateLimitBlock)
class RateLimitBlockAdmin(admin.ModelAdmin):
    list_display = ('rule', 'key', 'blocked_until', 'created_at')
    list_filter = ('rule', 'blocked_until', 'created_at')
    search_fields = ('key', 'rule__name')
    readonly_fields = AUDIT_READONLY_FIELDS
    ordering = ('-updated_at',)

    fieldsets = (
        (_('Rule & Target'), {
            'fields': ('rule', 'key'),
        }),
        (_('Blocking'), {
            'fields': ('blocked_until',),
        }),
        AUDIT_FIELDSET,
    )