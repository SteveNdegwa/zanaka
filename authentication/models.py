import base64
import binascii
import logging
import os
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel

logger = logging.getLogger(__name__)


class Identity(BaseModel):
    class Status(models.TextChoices):
        ACTIVATION_PENDING = 'ACTIVATION_PENDING', _('Activation Pending')
        ACTIVE = 'ACTIVE', _('Active')
        EXPIRED = 'EXPIRED', _('Expired')

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
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
        choices=Status.choices,
        default=Status.ACTIVATION_PENDING,
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
    def generate_token() -> Optional[str]:
        try:
            rand_part = binascii.hexlify(os.urandom(15)).decode()
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            raw = f'{rand_part}{timestamp}'
            return base64.urlsafe_b64encode(raw.encode()).decode()
        except Exception as ex:
            logger.exception('Identity.generate_token failed: %s', ex)
            return None

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                seconds=getattr(settings, 'TOKEN_VALIDITY_SECONDS', 3600)
            )
        super().save(*args, **kwargs)

    def extend(self):
        try:
            self.expires_at = timezone.now() + timedelta(
                seconds=getattr(settings, 'TOKEN_VALIDITY_SECONDS', 3600)
            )
            self.save(update_fields=['expires_at'])
        except Exception as ex:
            logger.exception('Identity.extend failed: %s', ex)
        return self


class LoginLog(BaseModel):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('Login Log')
        verbose_name_plural = _('Login Logs')

    def __str__(self) -> str:
        return f'{self.user.username} @ {self.created_at}'
