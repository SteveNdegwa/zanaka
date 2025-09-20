from typing import Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from authentication.models import Identity
from otps.models import OTP
from otps.services.otp_service import OTPService
from users.models import User
from users.services.device_service import DeviceService


class AuthService:
    @classmethod
    def login(cls, reg_number: str, password: str, source_ip: str, device_token: Optional[str]) -> Identity:
        user = User.objects.get(reg_number=reg_number, is_active=True)
        if not user or not user.check_password(password):
            raise ValidationError('Invalid credentials')

        device = DeviceService.create_device(
            user_id=user.id,
            device_token=device_token
        ) if device_token else None

        identity = Identity.objects.filter(
            user=user,
            device=device,
            expires_at__gte=timezone.now(),
            status=Identity.Status.ACTIVE
        ).order_by('-date_created').first()

        if identity is None:
            status = Identity.Status.ACTIVE if user.is_verified else Identity.Status.ACTIVATION_PENDING
            identity = Identity.objects.create(
                user=user,
                device=device,
                status=status,
            )
            if status == Identity.Status.ACTIVATION_PENDING:
                OTPService.send_otp(
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
    def logout(cls, user_id: str) -> None:
        user = User.objects.get(id=user_id, is_active=True)

        Identity.objects.filter(
            user=user, status=Identity.Status.ACTIVE
        ).update(status=Identity.Status.EXPIRED)

        return
