from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel


class Notification(BaseModel):
    class NotificationFrequency(models.TextChoices):
        ONCE = 'ONCE', _('Once')
        DAILY = 'DAILY', _('Daily')
        WEEKLY = 'WEEKLY', _('Weekly')
        MONTHLY = 'MONTHLY', _('Monthly')

    class DeliveryMethods(models.TextChoices):
        SMS = 'SMS', _('SMS')
        EMAIL = 'EMAIL', _('Email')
        PUSH = 'PUSH', _('Push')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        QUEUED = 'QUEUED', _('Queued')
        CONFIRMATION_PENDING = 'CONFIRMATION_PENDING', _('Confirmation Pending')
        SENT = 'SENT', _('Sent')
        FAILED = 'FAILED', _('Failed')

    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    delivery_method = models.CharField(
        max_length=10,
        choices=DeliveryMethods.choices,
        default=DeliveryMethods.PUSH,
        verbose_name=_('Delivery Method')
    )
    context = models.JSONField(default=dict, verbose_name=_('Context'))
    template = models.CharField(max_length=100, verbose_name=_('Template'))
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
        help_text=_('Unique key to identify the notification. Generated when saving the notification.'),
        verbose_name=_('Unique Key')
    )
    recipients = models.JSONField(
        default=list,
        help_text=_('List of recipients for the notification.'),
        verbose_name=_('Recipients')
    )
    sent_time = models.DateTimeField(blank=True, null=True, verbose_name=_('Sent Time'))
    response_data = models.JSONField(blank=True, null=True, verbose_name=_('Response Data'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_('Status'))

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date_created']),
            models.Index(fields=['unique_key'])
        ]
        ordering = ('-date_created',)
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f'{self.user} - {self.delivery_method}'
