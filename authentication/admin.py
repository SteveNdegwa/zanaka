from django.contrib import admin
from .models import Identity, LoginLog


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'status', 'token', 'expires_at', 'source_ip', 'created_at')
    list_filter = ('status', 'expires_at', 'created_at')
    search_fields = (
        'user__id', 'user__username',  'user__reg_number', 'user__first_name', 'user__last_name',
        'user__phone_number', 'device__token', 'token', 'source_ip'
    )
    readonly_fields = ('token', 'created_at', 'updated_at')

    fieldsets = (
        ('User & Status', {
            'fields': ('user', 'device', 'status')
        }),
        ('Token Info', {
            'fields': ('token', 'expires_at', 'source_ip'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-created_at',)


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)

    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
