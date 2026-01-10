import secrets
from datetime import timedelta
from typing import Optional

from django.db import models
from django.utils.translation import gettext_lazy as _
from base.models import BaseModel


class ApiClient(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Client Name'),
        help_text=_('Name of the external system or partner.')
    )
    api_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name=_('API Key'),
        help_text=_('Unique API key identifying this client.')
    )
    allowed_ips = models.TextField(
        blank=True,
        verbose_name=_('Allowed IPs'),
        help_text=_('Comma-separated list of allowed IPs for request validation.')
    )
    signature_secret = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Signature Secret'),
        help_text=_('Shared secret for HMAC signature validation of callbacks.')
    )
    signature_header_key = models.CharField(
        max_length=50,
        default='x-signature',
        verbose_name=_('Signature Header Key'),
        help_text=_('Header name containing the callback signature.')
    )
    signature_algorithm = models.CharField(
        max_length=20,
        choices=[('HMAC-SHA256', _('HMAC-SHA256')), ('RSA-SHA256', _('RSA-SHA256'))],
        default='HMAC-SHA256',
        verbose_name=_('Signature Algorithm'),
        help_text=_('Algorithm used to verify callback signatures.')
    )
    require_signature_verification = models.BooleanField(
        default=False,
        verbose_name=_('Require Signature Verification'),
        help_text=_('If True, incoming requests must include a valid cryptographic signature.')
    )
    meta = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Metadata'),
        help_text=_('Optional metadata about the client (contact info, environment, etc.).')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Designates whether this client is active.')
    )

    class Meta:
        verbose_name = _('API Client')
        verbose_name_plural = _('API Clients')
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

    def save(self, *args, **kwargs) -> None:
        if not self.api_key:
            self.api_key = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def get_active_public_key(self) -> Optional['ApiClientKey']:
        return self.keys.filter(is_active=True).order_by('-created_at').first()


class ApiClientKey(BaseModel):
    client = models.ForeignKey(
        ApiClient,
        on_delete=models.CASCADE,
        related_name='keys',
        verbose_name=_('API Client'),
        help_text=_('Owning API client for this key.')
    )
    public_key = models.TextField(
        verbose_name=_('Public Key'),
        help_text=_("The client's public key in PEM format.")
    )
    fingerprint = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name=_('Fingerprint'),
        help_text=_('SHA-256 fingerprint of the public key for quick lookup.')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Indicates if this key is currently active.')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expiration Time')
    )

    class Meta:
        verbose_name = _('API Client Key')
        verbose_name_plural = _('API Client Keys')
        unique_together = ['client', 'fingerprint']
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.client.name} [{self.fingerprint[:12]}...]'

    def deactivate_others(self) -> None:
        self.client.keys.exclude(id=self.id).update(is_active=False)

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.is_active:
            self.deactivate_others()


class SystemKey(BaseModel):
    name = models.CharField(
        max_length=100,
        unique=True,
        default='default',
        verbose_name=_('Key Name')
    )
    public_key = models.TextField(
        verbose_name=_('Public Key'),
        help_text=_('Public key (shared with partners).')
    )
    private_key = models.TextField(
        verbose_name=_('Private Key'),
        help_text=_('Private key')
    )
    fingerprint = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_('Fingerprint'),
        help_text=_('SHA-256 fingerprint of the public key.')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Expiration Time')
    )

    class Meta:
        verbose_name = _('System Key')
        verbose_name_plural = _('System Keys')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.name} [{self.fingerprint[:12]}...]'


class APICallback(BaseModel):
    client = models.ForeignKey(
        ApiClient,
        on_delete=models.CASCADE,
        related_name='callbacks',
        verbose_name=_('API Client'),
        help_text=_('API client associated with this callback.')
    )
    path = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_('Callback Path'),
        help_text=_('URL path pattern or endpoint for the callback.')
    )
    require_authentication = models.BooleanField(
        default=False,
        verbose_name=_('Require Authentication'),
        help_text=_('If True, the callback requires API key authentication.')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Indicates whether this callback is active.')
    )

    class Meta:
        verbose_name = _('API Callback')
        verbose_name_plural = _('API Callbacks')
        ordering = ['client__name', 'path']
        unique_together = ['client', 'path']

    def __str__(self) -> str:
        return f'{self.client.name} → {self.path} ({'Active' if self.is_active else 'Inactive'})'


class RateLimitRule(BaseModel):
    SCOPE_CHOICES = [
        ('global', _('Global')),
        ('api_client', _('API Client')),
        ('user', _('Per User')),
        ('ip', _('Per IP')),
        ('endpoint', _('Per Endpoint')),
        ('api_client_endpoint', _('API Client + Endpoint')),
        ('user_endpoint', _('Per User + Endpoint')),
        ('ip_endpoint', _('Per IP + Endpoint')),
    ]

    PERIOD_CHOICES = [
        ('second', _('Second')),
        ('minute', _('Minute')),
        ('hour', _('Hour')),
        ('day', _('Day')),
        ('week', _('Week')),
        ('month', _('Month')),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name=_('Rule Name'))
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, verbose_name=_('Scope'))
    limit = models.PositiveIntegerField(verbose_name=_('Limit'), help_text=_('Number of requests allowed'))
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, verbose_name=_('Period'))
    period_count = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Period Count'),
        help_text=_("Number of periods (e.g., 2 for '2 hours')")
    )
    endpoint_pattern = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Endpoint Pattern'),
        help_text=_('Regex pattern for URL matching')
    )
    http_methods = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('HTTP Methods'),
        help_text=_('Comma-separated HTTP methods (GET,POST,etc)')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active')
    )
    priority = models.IntegerField(
        default=0,
        verbose_name=_('Priority'),
        help_text=_('Higher priority rules are checked first')
    )
    block_duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Block Duration (Minutes)'),
        help_text=_('Block duration after limit exceeded (0 = no blocking)')
    )

    class Meta:
        verbose_name = _('Rate Limit Rule')
        verbose_name_plural = _('Rate Limit Rules')
        ordering = ['name', '-priority']

    def __str__(self) -> str:
        return f'{self.name}: {self.limit}/{self.period_count} {self.period}(s) - {self.scope}'

    def get_period_timedelta(self) -> timedelta:
        period_map = {
            'second': timedelta(seconds=self.period_count),
            'minute': timedelta(minutes=self.period_count),
            'hour': timedelta(hours=self.period_count),
            'day': timedelta(days=self.period_count),
            'week': timedelta(weeks=self.period_count),
            'month': timedelta(days=self.period_count * 30),
        }
        return period_map.get(self.period, timedelta(minutes=self.period_count))


class RateLimitAttempt(BaseModel):
    rule = models.ForeignKey(RateLimitRule, on_delete=models.CASCADE, verbose_name=_('Rule'))
    key = models.CharField(max_length=255, db_index=True, verbose_name=_('Key'))
    endpoint = models.CharField(max_length=200, blank=True, verbose_name=_('Endpoint'))
    method = models.CharField(max_length=10, verbose_name=_('HTTP Method'))
    count = models.PositiveIntegerField(default=1, verbose_name=_('Attempt Count'))
    window_start = models.DateTimeField(db_index=True, verbose_name=_('Window Start'))
    last_attempt = models.DateTimeField(auto_now=True, verbose_name=_('Last Attempt'))

    class Meta:
        verbose_name = _('Rate Limit Attempt')
        verbose_name_plural = _('Rate Limit Attempts')
        ordering = ['-last_attempt']
        unique_together = ['rule', 'key', 'endpoint', 'window_start']
        indexes = [
            models.Index(fields=['rule', 'key', 'window_start']),
            models.Index(fields=['window_start']),
        ]

    def __str__(self) -> str:
        return f'Attempt: {self.key} - {self.count} times for {self.rule.name}'


class RateLimitBlock(BaseModel):
    rule = models.ForeignKey(RateLimitRule, on_delete=models.CASCADE, verbose_name=_('Rule'))
    key = models.CharField(max_length=255, db_index=True, verbose_name=_('Key'))
    blocked_until = models.DateTimeField(db_index=True, verbose_name=_('Blocked Until'))

    class Meta:
        verbose_name = _('Rate Limit Block')
        verbose_name_plural = _('Rate Limit Blocks')
        ordering = ['-updated_at']
        unique_together = ['rule', 'key']

    def __str__(self) -> str:
        return f'Block: {self.key} until {self.blocked_until} by {self.rule.name}'
