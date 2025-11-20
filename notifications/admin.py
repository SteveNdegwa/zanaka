from django.contrib import admin
from .models import Template, Provider, Notification


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "notification_type", "subject", "is_active", "date_created")
    list_filter = ("notification_type", "is_active")
    search_fields = ("name", "subject", "body")
    ordering = ("-date_created",)

    fieldsets = (
        ("Template Details", {
            "fields": ("name", "notification_type", "subject", "body"),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Metadata", {
            "fields": ("date_created", "date_modified"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("date_created", "date_modified")


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "notification_type", "priority", "is_active", "date_created")
    list_filter = ("notification_type", "is_active")
    search_fields = ("name", "class_name")
    ordering = ("-date_created",)

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
            "fields": ("date_created", "date_modified"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("date_created", "date_modified")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "notification_type", "provider", "status", "frequency",
        "sent_time", "failure_message", "date_created"
    )
    list_filter = ("status", "frequency", "notification_type", "provider")
    search_fields = ("unique_key", "recipients", "context", "failure_message", "failure_traceback")
    ordering = ("-date_created",)

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
            "fields": ("date_created", "date_modified"),
            "classes": ("collapse",),
        }),
    )
    readonly_fields = ("date_created", "date_modified", "failure_traceback")
