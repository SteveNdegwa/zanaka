from django.contrib import admin
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
    fields = (
        'path',
        'require_authentication',
        'is_active',
    )
    readonly_fields = ('created_at', 'updated_at')


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
    list_filter = ('is_active', 'signature_algorithm', 'require_signature_verification')
    readonly_fields = ('api_key', 'created_at', 'updated_at')
    inlines = [ApiClientKeyInline, ApiCallbackInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'is_active', 'created_at', 'updated_at')
        }),
        ('API Settings', {
            'fields': ('api_key', 'allowed_ips', 'meta')
        }),
        ('Signature Configuration', {
            'fields': (
                'signature_algorithm',
                'signature_secret',
                'signature_header_key',
                'require_signature_verification'
            )
        }),
    )


@admin.register(ApiClientKey)
class ApiClientKeyAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'fingerprint',
        'is_active',
        'expires_at',
        'created_at',
    )
    list_filter = ('is_active', 'expires_at')
    search_fields = ('fingerprint', 'client__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Key Info', {
            'fields': ('client', 'public_key', 'fingerprint', 'is_active')
        }),
        ('Validity', {
            'fields': ('expires_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-created_at',)


@admin.register(SystemKey)
class SystemKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'fingerprint', 'is_active', 'expires_at', 'created_at', 'updated_at')
    search_fields = ('name', 'fingerprint')
    list_filter = ('is_active',)
    readonly_fields = ('fingerprint', 'created_at', 'updated_at')

    fieldsets = (
        ('Key Info', {
            'fields': ('name', 'public_key', 'private_key', 'fingerprint', 'created_at', 'updated_at')
        }),
        ('Status', {
            'fields': ('is_active', 'expires_at')
        }),
    )


@admin.register(APICallback)
class APICallbackAdmin(admin.ModelAdmin):
    list_display = (
        'client',
        'path',
        'require_authentication',
        'is_active',
        'created_at',
    )
    list_filter = ('require_authentication', 'is_active')
    search_fields = ('path', 'client__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Callback Info', {
            'fields': ('client', 'path', 'is_active')
        }),
        ('Security', {
            'fields': ('require_authentication',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('client__name', 'path')


@admin.register(RateLimitRule)
class RateLimitRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'scope', 'limit', 'period_count', 'period',
        'is_active', 'priority', 'block_duration_minutes', 'created_at'
    )
    list_filter = ('scope', 'period', 'is_active', 'created_at')
    search_fields = ('name', 'endpoint_pattern', 'http_methods')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('General', {
            'fields': ('name', 'scope', 'is_active', 'priority')
        }),
        ('Limits', {
            'fields': ('limit', 'period_count', 'period', 'block_duration_minutes')
        }),
        ('Targeting', {
            'fields': ('endpoint_pattern', 'http_methods')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-priority', 'name')


@admin.register(RateLimitAttempt)
class RateLimitAttemptAdmin(admin.ModelAdmin):
    list_display = ('rule', 'key', 'endpoint', 'method', 'count', 'window_start', 'last_attempt')
    list_filter = ('method', 'window_start')
    search_fields = ('key', 'endpoint', 'rule__name')
    readonly_fields = ('created_at', 'updated_at', 'last_attempt')

    fieldsets = (
        ('Rule & Target', {
            'fields': ('rule', 'key', 'endpoint', 'method')
        }),
        ('Attempt Info', {
            'fields': ('count', 'window_start', 'last_attempt')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-last_attempt',)


@admin.register(RateLimitBlock)
class RateLimitBlockAdmin(admin.ModelAdmin):
    list_display = ('rule', 'key', 'blocked_until', 'created_at')
    list_filter = ('blocked_until', 'created_at')
    search_fields = ('key', 'rule__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Rule & Target', {
            'fields': ('rule', 'key')
        }),
        ('Blocking', {
            'fields': ('blocked_until',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-updated_at',)
