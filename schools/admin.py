from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import School, Branch, Classroom


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ('name', 'location', 'principal', 'capacity', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


class ClassroomInline(admin.TabularInline):
    model = Classroom
    extra = 0
    fields = ('name', 'grade_level', 'capacity', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    show_change_link = True


AUDIT_FIELDSET = (
    _("Audit"),
    {
        "fields": ("id", "created_at", "updated_at", "synced"),
        "classes": ("collapse",),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'colored_status',
        'contact_email',
        'contact_phone',
        'established_date',
        'branches_count',
    )
    list_filter = ('is_active', 'established_date', 'created_at')
    search_fields = ('name', 'code', 'contact_email', 'contact_phone')
    readonly_fields = AUDIT_READONLY_FIELDS
    inlines = [BranchInline]
    ordering = ('name',)

    fieldsets = (
        (_("School Information"), {
            'fields': (
                'name', 'code', 'address',
                ('contact_email', 'contact_phone'),
                'established_date', 'is_active'
            )
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        color = "green" if obj.is_active else "red"
        status = _("Active") if obj.is_active else _("Inactive")
        return format_html('<b style="color:{};">{}</b>', color, status)
    colored_status.short_description = _("Status")

    def branches_count(self, obj):
        count = obj.branches.count()
        url = f"{obj.id}/branch/?school__id__exact={obj.id}"
        return format_html('<a href="{}">{} {}</a>', url, count, _("branches"))
    branches_count.short_description = _("Branches")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'school_link',
        'location',
        'principal_link',
        'colored_status',
        'capacity',
        'classrooms_count',
        'created_at',
    )
    list_filter = ('school', 'is_active', 'principal', 'established_date')
    search_fields = (
        'name', 'school__name', 'location',
        'principal__username', 'principal__first_name', 'principal__last_name'
    )
    autocomplete_fields = ('school', 'principal')
    readonly_fields = AUDIT_READONLY_FIELDS
    inlines = [ClassroomInline]
    ordering = ('school__name', 'name')

    fieldsets = (
        (_("Branch Information"), {
            'fields': (
                'name', 'school', 'location',
                ('contact_email', 'contact_phone'),
                'principal', 'capacity', 'established_date', 'is_active'
            )
        }),
        AUDIT_FIELDSET,
    )

    def school_link(self, obj):
        url = f"/admin/schools/school/{obj.school.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.school.name)
    school_link.short_description = _("School")
    school_link.admin_order_field = 'school__name'

    def principal_link(self, obj):
        if not obj.principal:
            return "—"
        url = f"/admin/users/user/{obj.principal.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.principal.full_name or obj.principal.username)
    principal_link.short_description = _("Principal")

    def colored_status(self, obj):
        color = "green" if obj.is_active else "red"
        status = _("Active") if obj.is_active else _("Inactive")
        return format_html('<b style="color:{};">{}</b>', color, status)
    colored_status.short_description = _("Status")

    def classrooms_count(self, obj):
        count = obj.classrooms.count()
        url = f"/admin/schools/classroom/?branch__id__exact={obj.id}"
        return format_html('<a href="{}">{} {}</a>', url, count, _("classrooms"))
    classrooms_count.short_description = _("Classrooms")


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'branch_link',
        'grade_level_badge',
        'capacity',
        'colored_status',
        'created_at',
    )
    list_filter = ('branch__school', 'branch', 'grade_level', 'is_active', 'created_at')
    search_fields = ('name', 'branch__name', 'branch__school__name')
    autocomplete_fields = ('branch',)
    readonly_fields = AUDIT_READONLY_FIELDS
    ordering = ('branch__school__name', 'branch__name', 'name')

    fieldsets = (
        (_("Classroom Information"), {
            'fields': ('name', 'branch', 'grade_level', 'capacity', 'is_active')
        }),
        AUDIT_FIELDSET,
    )

    def branch_link(self, obj):
        url = f"/admin/schools/branch/{obj.branch.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.branch.name)
    branch_link.short_description = _("Branch")
    branch_link.admin_order_field = 'branch__name'

    def grade_level_badge(self, obj):
        colors = {
            'baby_class': '#ff9999',
            'pp_1': '#ffcc99',
            'pp_2': '#ffff99',
            'grade_1': '#ccff99',
            'grade_2': '#99ff99',
            'grade_3': '#99ffcc',
            'grade_4': '#99ffff',
            'grade_5': '#99ccff',
            'grade_6': '#9999ff',
            'grade_7': '#cc99ff',
            'grade_8': '#ff99ff',
            'grade_9': '#ff99cc',
        }
        color = colors.get(obj.grade_level, 'gray')
        display = obj.get_grade_level_display()
        return format_html(
            '<span style="background:{}; color:black; padding:3px 8px; border-radius:4px; font-weight:bold;">{}</span>',
            color, display
        )
    grade_level_badge.short_description = _("Grade Level")

    def colored_status(self, obj):
        color = "green" if obj.is_active else "red"
        status = _("Active") if obj.is_active else _("Inactive")
        return format_html('<b style="color:{};">{}</b>', color, status)
    colored_status.short_description = _("Status")
