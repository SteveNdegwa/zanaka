from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel


class OTPPurpose(models.TextChoices):
    PHONE_VERIFICATION = 'PHONE_VERIFICATION', _('Phone Verification')
    EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', _('Email Verification')
    TWO_FACTOR_AUTHENTICATION = 'TWO_FACTOR_AUTHENTICATION', _('Two-Factor Authentication')
    PASSWORD_RESET = 'PASSWORD_RESET', _('Password Reset')


class OTPDeliveryMethod(models.TextChoices):
    SMS = 'SMS', _('SMS')
    EMAIL = 'EMAIL', _('Email')


class OTP(BaseModel):
    user = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='otps',
        verbose_name=_('User')
    )
    purpose = models.CharField(
        max_length=32,
        choices=OTPPurpose.choices,
        verbose_name=_('Purpose')
    )
    identity = models.ForeignKey(
        'authentication.Identity',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='otps',
        verbose_name=_('Identity')
    )
    code = models.CharField(
        max_length=255,
        verbose_name=_('Code'),
        help_text=_('Hashed OTP code')
    )
    delivery_method = models.CharField(
        max_length=10,
        choices=OTPDeliveryMethod.choices,
        verbose_name=_('Delivery Method')
    )
    contact = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Contact'),
        help_text=_('Phone number in E.164 format or email address')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires At'),
        help_text=_('OTP becomes invalid after this time')
    )
    is_used = models.BooleanField(default=False,verbose_name=_('Is Used'))
    retry_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Retry Count'),
        help_text=_('Number of failed validation attempts')
    )

    class Meta:
        verbose_name = _('OTP')
        verbose_name_plural = _('OTPs')
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'purpose', 'is_used', 'expires_at']),
            models.Index(fields=['identity', 'purpose']),
            models.Index(fields=['contact', 'purpose', '-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_used', 'created_at']),
            models.Index(fields=['purpose', 'delivery_method']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(identity__isnull=False),
                name='otp_must_have_user_or_identity'
            )
        ]

    def __str__(self) -> str:
        target = (
            self.user.full_name or self.user.username if self.user
            else self.contact or _('Anonymous')
        )
        status = _('Used') if self.is_used else _('Active')
        if self.is_expired:
            status = _('Expired')
        return f"OTP {self.get_purpose_display()} → {target} ({status})"

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and timezone.now() > self.expires_at
