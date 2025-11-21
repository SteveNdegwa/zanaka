from django.contrib import admin
from .models import Template, Provider, Notification


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "notification_type", "subject", "is_active", "created_at")
    list_filter = ("notification_type", "is_active")
    search_fields = ("name", "subject", "body")
    ordering = ("-created_at",)

    fieldsets = (
        ("Template Details", {
            "fields": ("name", "notification_type", "subject", "body"),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "notification_type", "priority", "is_active", "created_at")
    list_filter = ("notification_type", "is_active")
    search_fields = ("name", "class_name")
    ordering = ("-created_at",)

    fieldsets = (
        ("Provider Details", {
            "fields": ("name", "notification_type", "priority", "class_name"),
        }),
        ("Configuration", {
            "fields": ("config",),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "notification_type", "provider", "status", "frequency",
        "sent_time", "failure_message", "created_at"
    )
    list_filter = ("status", "frequency", "notification_type", "provider")
    search_fields = ("unique_key", "recipients", "context", "failure_message", "failure_traceback")
    ordering = ("-created_at",)

    fieldsets = (
        ("Notification Details", {
            "fields": (
                "user", "notification_type", "template", "provider",
                "recipients", "context", "frequency"
            ),
        }),
        ("Tracking & Status", {
            "fields": ("unique_key", "sent_time", "status", "failure_message", "failure_traceback"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("created_at", "updated_at", "failure_traceback")
