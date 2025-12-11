from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from authentication.models import Identity, IdentityStatus
from base.services.base_services import BaseServices
from base.services.system_settings_cache import SystemSettingsCache
from otps.models import OTPPurpose, OTPDeliveryMethod
from otps.services.otp_services import OTPServices
from users.models import User
from users.services.device_services import DeviceServices


class AuthServices(BaseServices):
    @classmethod
    @transaction.atomic
    def login(cls, credential: str, password: str, source_ip: str, device_token: Optional[str]) -> Identity:
        """
        Authenticate a user using either their registration number or username and issue a new identity.

        :param credential: The login credential, which may be either the user's reg_number or username.
        :type credential: str
        :param password: The user's password for authentication.
        :type password: str
        :param source_ip: The IP address from which the login request originated.
        :type source_ip: str
        :param device_token: Optional device token used to associate the identity with a specific device.
        :type device_token: Optional[str]
        :raises ValidationError: If the user does not exist, is inactive, or the password is invalid.
        :rtype: Identity
        :return: An Identity object representing the user's authenticated session.
        """
        try:
            user = User.objects.get(
                Q(reg_number=credential) | Q(username=credential),
                is_active=True
            )
        except User.DoesNotExist:
            user = None

        if not user or not user.check_password(password):
            raise ValidationError('Invalid credentials')

        device = DeviceServices.add_device(
            user=user,
            device_token=device_token
        ) if device_token else None

        identity = Identity.objects.filter(
            user=user,
            device=device,
            expires_at__gte=timezone.now(),
            status=IdentityStatus.ACTIVE
        ).order_by('-created_at').first()

        if identity is None:
            if SystemSettingsCache.get().two_factor_authentication_required:
                status = IdentityStatus.ACTIVATION_PENDING
            else:
                status = IdentityStatus.ACTIVE
            identity = Identity.objects.create(
                user=user,
                device=device,
                status=status,
            )
            if status == IdentityStatus.ACTIVATION_PENDING:
                OTPServices.send_otp(
                    purpose=OTPPurpose.TWO_FACTOR_AUTHENTICATION,
                    token=identity.token,
                    delivery_method=OTPDeliveryMethod.EMAIL
                )

        Identity.objects.filter(
            user=user,
            status=IdentityStatus.ACTIVE
        ).exclude(id=identity.id).update(status=IdentityStatus.EXPIRED)

        identity.source_ip = source_ip
        identity.extend()

        return identity

    @classmethod
    @transaction.atomic
    def logout(cls, user: User) -> None:
        """
        Log out a user by expiring the identity associated with the provided token.

        :param user: The user to logout.
        :type user: User
        :raises Identity.DoesNotExist: If no active identity exists for the given token.
        :rtype: None
        """
        identity = Identity.objects.get(user=user, status=IdentityStatus.ACTIVE)
        identity.status = IdentityStatus.EXPIRED
        identity.save(update_fields=['status'])
