import base64
import binascii
import datetime
import os
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel
from base.services.system_settings_cache import SystemSettingsCache


class IdentityStatus(models.TextChoices):
    ACTIVATION_PENDING = 'ACTIVATION_PENDING', _('Activation Pending')
    ACTIVE = 'ACTIVE', _('Active')
    EXPIRED = 'EXPIRED', _('Expired')


class Identity(BaseModel):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    device = models.ForeignKey(
        'users.Device',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Device')
    )
    token = models.CharField(max_length=200, unique=True, verbose_name=_('Token'))
    expires_at = models.DateTimeField(verbose_name=_('Expiration Time'))
    source_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('Source IP'))
    status = models.CharField(
        max_length=20,
        choices=IdentityStatus.choices,
        default=IdentityStatus.ACTIVATION_PENDING,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('Identity')
        verbose_name_plural = _('Identities')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['token', 'status']),
            models.Index(fields=['user', 'device', 'status']),
        ]

    def __str__(self) -> str:
        return f'{self.user.username} - {self.status}'

    @staticmethod
    def generate_token() -> str:
        rand_part = binascii.hexlify(os.urandom(15)).decode()
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        raw = f'{rand_part}{timestamp}'
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @property
    def _expires_at(self) -> datetime.datetime:
        token_validity_seconds = SystemSettingsCache.get().auth_token_validity_seconds
        return timezone.now() + timedelta(seconds=token_validity_seconds)

    def save(self, *args, **kwargs) -> None:
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = self._expires_at
        super().save(*args, **kwargs)

    def extend(self) -> None:
        self.expires_at = self._expires_at
        self.save(update_fields=['expires_at'])
        self.user.update_last_activity()
