import uuid

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from audit.mixins import AuditableMixin


class BaseModel(AuditableMixin, models.Model):
    id = models.UUIDField(
        max_length=100,
        default=uuid.uuid4,
        unique=True,
        editable=False,
        primary_key=True,
        verbose_name=_('Unique identifier')
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Date modified'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    synced = models.BooleanField(
        default=False,
        verbose_name=_('Synced'),
        help_text=_('Indicates whether this record has been synchronized with the replica system.')
    )

    objects = models.Manager()

    class Meta(object):
        abstract = True


class GenericBaseModel(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    description = models.CharField(max_length=100, blank=True, verbose_name=_('Description'))

    class Meta(object):
        abstract = True


def default_api_key_exempt_paths():
    return ['/cia', '/health', '/static', '/media', '/__debug__', '/favicon.ico']

def default_csrf_exempt_paths():
    return ['/api/']

def default_save_request_log_exempt_paths():
    return []


class SystemSettings(BaseModel):
    system_name = models.CharField(
        max_length=100,
        default='Zanaka',
        verbose_name=_('System Name'),
        help_text=_('The name of the system/application.')
    )

    # Cookies settings
    cookie_secure = models.BooleanField(
        default=False,
        verbose_name=_('Secure Cookies'),
        help_text=_('Whether auth cookies should be sent over HTTPS only.')
    )
    auth_token_cookie_name = models.CharField(
        max_length=50,
        default='auth_token',
        verbose_name=_('Auth Token Cookie Name'),
        help_text=_('Name of the cookie used to store authentication token.')
    )

    # Authentication settings
    auth_token_validity_seconds = models.IntegerField(
        default=300,
        verbose_name=_('Auth Token Validity (Seconds)'),
        help_text=_('Duration in seconds before an auth token expires.')
    )
    auth_token_allow_header_fallback = models.BooleanField(
        default=True,
        verbose_name=_('Allow Header Fallback'),
        help_text=_('Allow authentication token to be passed in headers as a fallback.')
    )
    two_factor_authentication_required = models.BooleanField(
        default=True,
        verbose_name=_('Require Two-Factor Authentication'),
        help_text=_('Require 2FA for user logins.')
    )

    # OTP settings
    otp_length = models.IntegerField(
        default=4,
        verbose_name=_('OTP Length'),
        help_text=_('Number of digits in generated OTPs.')
    )
    otp_validity_seconds = models.IntegerField(
        default=300,
        verbose_name=_('OTP Validity (Seconds)'),
        help_text=_('Time in seconds before OTP expires.')
    )
    action_otp_validity_seconds = models.IntegerField(
        default=300,
        verbose_name=_('Action OTP Validity (Seconds)'),
        help_text=_('Time in seconds before OTP for specific actions expires.')
    )
    max_otp_attempts = models.IntegerField(
        default=5,
        verbose_name=_('Max OTP Attempts'),
        help_text=_('Maximum number of allowed OTP verification attempts.')
    )

    # API Gateway settings
    encrypted_header = models.CharField(
        max_length=50,
        default='X-Encrypted',
        verbose_name=_('Encrypted Header'),
        help_text=_('Header name used to indicate encrypted requests.')
    )
    api_key_header = models.CharField(
        max_length=50,
        default='X-Api-Key',
        verbose_name=_('API Key Header'),
        help_text=_('Header name used for API key authentication.')
    )
    api_key_verification_required = models.BooleanField(
        default=False,
        verbose_name=_('API Key Verification Required'),
        help_text=_('Require incoming API requests to include a valid API key.')
    )
    api_key_verification_exempt_paths = models.JSONField(
        default=default_api_key_exempt_paths,
        verbose_name=_('API Key Validation Exempt Paths'),
        help_text=_('List of URL paths exempted from API key validation.'),
    )
    signature_verification_required = models.BooleanField(
        default=False,
        verbose_name=_('Signature Verification Required'),
        help_text=_('Require incoming API requests to include a valid cryptographic signature.')
    )
    csrf_exempt_paths = models.JSONField(
        default=default_csrf_exempt_paths,
        verbose_name=_('CSRF Exempt Paths'),
        help_text=_('List of URL paths that bypass CSRF validation.')
    )
    save_request_log_exempt_paths = models.JSONField(
        default=default_save_request_log_exempt_paths,
        verbose_name=_('Save Request Log Exempt Paths'),
        help_text=_('List of URL paths exempted from request logging.'),
    )

    # Notification settings
    send_notifications_async = models.BooleanField(
        default=False,
        verbose_name=_('Send Notifications Asynchronously'),
        help_text=_('Send notifications asynchronously if True.')
    )

    class Meta:
        verbose_name = _('System Setting')
        verbose_name_plural = _('System Settings')

    def __str__(self) -> str:
        return f'{self.system_name} Settings'

    def save(self, *args, **kwargs):
        if SystemSettings.objects.exists() and not self.pk:
            raise ValidationError(_('Only one SystemSettings instance is allowed.'))
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> 'SystemSettings':
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj
