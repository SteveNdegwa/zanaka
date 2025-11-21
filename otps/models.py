from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel


class OTP(BaseModel):
    class PurposeTypes(models.TextChoices):
        PHONE_VERIFICATION = 'phone_verification', _('Phone Verification')
        EMAIL_VERIFICATION = 'email_verification', _('Email Verification')
        TWO_FACTOR_AUTHENTICATION = '2fa', _('Two-Factor Authentication')
        PASSWORD_RESET = 'password_reset', _('Password Reset')

    class DeliveryMethods(models.TextChoices):
        SMS = 'sms', _('SMS')
        EMAIL = 'email', _('Email')

    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    purpose = models.CharField(max_length=32, choices=PurposeTypes.choices, verbose_name=_('Purpose'))
    identity = models.ForeignKey(
        'authentication.Identity',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='otps',
        verbose_name=_('Identity')
    )
    code = models.CharField(max_length=255, verbose_name=_('Code'), help_text=_('Hashed OTP code'))
    delivery_method = models.CharField(
        max_length=10,
        choices=DeliveryMethods.choices,
        verbose_name=_('Delivery Method')
    )
    contact = models.CharField(
        max_length=255,
        verbose_name=_('Contact'),
        help_text=_('Phone number or email address')
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Expires At'))
    is_used = models.BooleanField(default=False, verbose_name=_('Is Used'))
    retry_count = models.IntegerField(default=0, verbose_name=_('Retry Count'))

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('OTP')
        verbose_name_plural = _('OTPs')

    def is_expired(self):
        return timezone.now() > self.expires_at
