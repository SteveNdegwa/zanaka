from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel


class RequestLog(BaseModel):
    request_id = models.UUIDField(editable=False, verbose_name=_('Request ID'))
    api_client = models.ForeignKey(
        'api.APIClient',
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('API Client')
    )
    user = models.ForeignKey(
        'users.User',
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('User')
    )
    token = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Token'))
    is_authenticated = models.BooleanField(default=False, verbose_name=_('Is Authenticated'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(null=True, blank=True, verbose_name=_('User Agent'))
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name=_('Session Key'))
    request_method = models.CharField(max_length=10, verbose_name=_('Request Method'))
    request_path = models.TextField(verbose_name=_('Request Path'))
    request_data = models.JSONField(null=True, blank=True, verbose_name=_('Request Data'))
    is_secure = models.BooleanField(default=False, verbose_name=_('Is Secure'))
    view_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('View Name'))
    view_args = models.JSONField(null=True, blank=True, verbose_name=_('View Args'))
    view_kwargs = models.JSONField(null=True, blank=True, verbose_name=_('View Kwargs'))
    activity_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Activity Name'))
    exception_type = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Exception Type'))
    exception_message = models.TextField(null=True, blank=True, verbose_name=_('Exception Message'))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    time_taken = models.FloatField(null=True, blank=True, verbose_name=_('Time Taken (s)'))
    response_status = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_('Response Status'))
    response_data = models.JSONField(null=True, blank=True, verbose_name=_('Response Data'))

    class Meta:
        ordering = ['-started_at']
        verbose_name = _('Request Log')
        verbose_name_plural = _('Request Logs')
        indexes = [
            models.Index(fields=['started_at']),
            models.Index(fields=['ended_at']),
            models.Index(fields=['time_taken']),
            models.Index(fields=['request_method']),
            models.Index(fields=['is_authenticated']),
            models.Index(fields=['activity_name']),
            models.Index(fields=['view_name']),
        ]

    def __str__(self) -> str:
        return f'RequestLog {self.request_id} - {self.request_method} {self.request_path}'


class AuditEventType(models.TextChoices):
    CREATE = 'CREATE', _('Create')
    UPDATE = 'UPDATE', _('Update')
    DELETE = 'DELETE', _('Delete')
    VIEW = 'VIEW', _('View')
    LOGIN = 'LOGIN', _('Login')
    LOGOUT = 'LOGOUT', _('Logout')
    PERMISSION_CHANGE = 'PERMISSION_CHANGE', _('Permission Change')
    DATA_EXPORT = 'DATA_EXPORT', _('Data Export')
    BULK_OPERATION = 'BULK_OPERATION', _('Bulk Operation')
    SYSTEM_EVENT = 'SYSTEM_EVENT', _('System Event')
    SECURITY_EVENT = 'SECURITY_EVENT', _('Security Event')


class AuditSeverity(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    CRITICAL = 'CRITICAL', _('Critical')


class AuditLog(BaseModel):
    request_id = models.UUIDField(null=True, blank=True, verbose_name=_('Request ID'))
    api_client = models.ForeignKey(
        'api.APIClient',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('API Client')
    )
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('User')
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(null=True, blank=True, verbose_name=_('User Agent'))
    request_method = models.CharField(max_length=10, null=True, blank=True, verbose_name=_('Request Method'))
    request_path = models.TextField(null=True, blank=True, verbose_name=_('Request Path'))
    activity_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Activity Name'))
    event_type = models.CharField(
        max_length=50,
        choices=AuditEventType.choices,
        db_index=True,
        verbose_name=_('Event Type')
    )
    severity = models.CharField(
        max_length=20,
        choices=AuditSeverity.choices,
        default=AuditSeverity.LOW,
        db_index=True,
        verbose_name=_('Severity')
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Content Type')
    )
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Object Representation')
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        verbose_name=_('Changes')
    )
    metadata = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        verbose_name=_('Metadata')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        indexes = [
            models.Index(fields=['created_at', 'event_type']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['user']),
            models.Index(fields=['request_id']),
        ]

    def __str__(self) -> str:
        actor = self.user or 'System'
        return f'{self.created_at} - {self.event_type} by {actor}'


class AuditConfiguration(BaseModel):
    model_name = models.CharField(max_length=100, unique=True, verbose_name=_('Model Name'))
    app_label = models.CharField(max_length=100, verbose_name=_('App Label'))
    is_enabled = models.BooleanField(default=True, verbose_name=_('Is Enabled'))
    track_create = models.BooleanField(default=True, verbose_name=_('Track Create'))
    track_update = models.BooleanField(default=True, verbose_name=_('Track Update'))
    track_delete = models.BooleanField(default=True, verbose_name=_('Track Delete'))
    excluded_fields = models.JSONField(default=list, blank=True, verbose_name=_('Excluded Fields'))
    retention_days = models.PositiveIntegerField(default=2555, verbose_name=_('Retention Days'))

    class Meta:
        unique_together = ('app_label', 'model_name')
        ordering = ['app_label', 'model_name']
        verbose_name = _('Audit Configuration')
        verbose_name_plural = _('Audit Configurations')

    def __str__(self) -> str:
        return f'{self.app_label}.{self.model_name}'
