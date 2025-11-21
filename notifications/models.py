from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel, GenericBaseModel


class NotificationType(models.TextChoices):
    EMAIL = 'email', _('Email')
    SMS = 'sms', _('SMS')


class NotificationFrequency(models.TextChoices):
    ONCE = 'once', _('Once')
    DAILY = 'daily', _('Daily')
    WEEKLY = 'weekly', _('Weekly')
    MONTHLY = 'monthly', _('Monthly')


class NotificationStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    QUEUED = 'queued', _('Queued')
    CONFIRMATION_PENDING = 'confirmation_pending', _('Confirmation Pending')
    SENT = 'sent', _('Sent')
    FAILED = 'failed', _('Failed')


class Template(GenericBaseModel):
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-created_at',)


class Provider(GenericBaseModel):
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices)
    priority = models.IntegerField(null=True, blank=True)
    config = models.JSONField()
    is_active = models.BooleanField(default=True)
    class_name = models.CharField(max_length=100,  help_text='Callback class containing its config')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-created_at',)


class Notification(BaseModel):
    user = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=10, choices=NotificationType.choices)
    template = models.ForeignKey(Template, null=True, on_delete=models.SET_NULL)
    provider = models.ForeignKey(Provider, null=True, on_delete=models.SET_NULL)
    recipients = models.JSONField(default=list)
    context = models.JSONField()
    frequency = models.CharField(
        max_length=20,
        choices=NotificationFrequency.choices,
        default=NotificationFrequency.ONCE
    )
    unique_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text='Unique key to identify the notification.')
    sent_time = models.DateTimeField(blank=True, null=True)
    failure_message = models.CharField(max_length=255, null=True, blank=True)
    failure_traceback = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['unique_key'])
        ]
        ordering = ('-created_at',)

    def _str_(self):
        return '%s - %s' % (self.notification_type, self.recipients)
