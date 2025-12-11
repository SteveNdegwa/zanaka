from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel, GenericBaseModel


class NotificationType(models.TextChoices):
    EMAIL = 'EMAIL', _('Email')
    SMS = 'SMS', _('SMS')


class NotificationFrequency(models.TextChoices):
    ONCE = 'ONCE', _('Once')
    DAILY = 'DAILY', _('Daily')
    WEEKLY = 'WEEKLY', _('Weekly')
    MONTHLY = 'MONTHLY', _('Monthly')


class NotificationStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    QUEUED = 'QUEUED', _('Queued')
    CONFIRMATION_PENDING = 'CONFIRMATION_PENDING', _('Confirmation Pending')
    SENT = 'SENT', _('Sent')
    FAILED = 'FAILED', _('Failed')


class Template(GenericBaseModel):
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        verbose_name=_('Notification Type')
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Subject')
    )
    body = models.TextField(
        verbose_name=_('Body')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )

    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return self.name


class Provider(GenericBaseModel):
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        verbose_name=_('Notification Type')
    )
    priority = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_('Priority'),
        help_text=_('Lower number = higher priority')
    )
    config = models.JSONField(
        default=dict,
        verbose_name=_('Configuration'),
        help_text=_('Provider-specific settings (API keys, endpoints, etc.)')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    class_name = models.CharField(
        max_length=100,
        verbose_name=_('Callback Class'),
        help_text=_("Name of the provider's class")
    )

    class Meta:
        verbose_name = _('Notification Provider')
        verbose_name_plural = _('Notification Providers')
        ordering = ('priority', 'name')
        unique_together = ('notification_type', 'class_name')

    def __str__(self) -> str:
        return f"{self.name} ({self.get_notification_type_display()})"


class Notification(BaseModel):
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        verbose_name=_('Notification Type')
    )
    template = models.ForeignKey(
        Template,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications',
        verbose_name=_('Template')
    )
    provider = models.ForeignKey(
        Provider,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications',
        verbose_name=_('Provider')
    )
    recipients = models.JSONField(
        default=list,
        verbose_name=_('Recipients'),
        help_text=_('List of emails or phone numbers')
    )
    context = models.JSONField(
        default=dict,
        verbose_name=_('Template Context'),
        help_text=_('Variables to render in the template')
    )
    frequency = models.CharField(
        max_length=20,
        choices=NotificationFrequency.choices,
        default=NotificationFrequency.ONCE,
        verbose_name=_('Frequency')
    )
    unique_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_('Unique Key'),
        help_text=_('Prevents duplicate notifications')
    )
    sent_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Sent At')
    )
    failure_message = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Failure Message')
    )
    failure_traceback = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Failure Traceback')
    )
    status = models.CharField(
        max_length=30,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name=_('Status'),
        db_index=True
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['unique_key']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['notification_type', 'status']),
        ]
        ordering = ('-created_at',)

    def __str__(self) -> str:
        recipient = self.recipients[0] if self.recipients else 'No recipient'
        return f"{self.get_notification_type_display()} → {recipient} ({self.get_status_display()})"