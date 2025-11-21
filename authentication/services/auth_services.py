from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from authentication.models import Identity
from base.services.base_services import BaseServices
from otps.models import OTP
from otps.services.otp_services import OTPServices
from users.models import User
from users.services.device_services import DeviceServices


class AuthServices(BaseServices):
    @classmethod
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
        user = User.objects.get(
            Q(reg_number=credential) | Q(username=credential),
            is_active=True
        )
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
            status=Identity.Status.ACTIVE
        ).order_by('-created_at').first()

        if identity is None:
            status = Identity.Status.ACTIVATION_PENDING if settings.TWO_FACTOR_AUTHENTICATION_REQUIRED else \
                Identity.Status.ACTIVE
            identity = Identity.objects.create(
                user=user,
                device=device,
                status=status,
            )
            if status == Identity.Status.ACTIVATION_PENDING:
                OTPServices.send_otp(
                    purpose=OTP.PurposeTypes.TWO_FACTOR_AUTHENTICATION,
                    token=identity.token
                )

        Identity.objects.filter(
            user=user,
            status=Identity.Status.ACTIVE
        ).exclude(id=identity.id).update(status=Identity.Status.EXPIRED)

        identity.source_ip = source_ip
        identity.extend()

        user.update_last_activity()

        return identity

    @classmethod
    def logout(cls, user: User) -> None:
        """
        Log out a user by expiring the identity associated with the provided token.

        :param user: The user to logout.
        :type user: User
        :raises Identity.DoesNotExist: If no active identity exists for the given token.
        :rtype: None
        """
        identity = Identity.objects.get(user=user, status=Identity.Status.ACTIVE)
        identity.status = Identity.Status.EXPIRED
        identity.save(update_fields=['status'])
