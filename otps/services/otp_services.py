import hashlib
from datetime import timedelta
from random import randint
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from authentication.models import Identity, IdentityStatus
from base.services.base_services import BaseServices
from base.services.system_settings_cache import SystemSettingsCache
from notifications.services.notification_services import NotificationServices
from otps.models import OTP, OTPPurpose, OTPDeliveryMethod
from users.models import User
from users.services.user_services import UserServices


class OTPServices(BaseServices):
    @classmethod
    def _generate_raw_code(cls, otp_length: int = 4) -> str:
        """
        Generate a random numeric OTP of a given length.

        :param otp_length: The number of digits in the OTP (must be >= 1).
        :type otp_length: int
        :raises ValidationError: If the OTP length is less than 1.
        :return: A randomly generated OTP as a string.
        :rtype: str
        """
        if otp_length < 1:
            raise ValidationError('OTP length must be at least 1')

        lower_bound = 10 ** (otp_length - 1)
        upper_bound = (10 ** otp_length) - 1

        return str(randint(lower_bound, upper_bound))

    @classmethod
    def _hash_code(cls, raw_code: str) -> str:
        """
        Hash an OTP code using SHA-256.

        :param raw_code: The raw OTP code to hash.
        :type raw_code: str
        :return: A SHA-256 hashed representation of the OTP.
        :rtype: str
        """
        return hashlib.sha256(raw_code.encode()).hexdigest()

    @classmethod
    @transaction.atomic
    def send_otp(
        cls,
        purpose: str,
        delivery_method: str,
        contact: Optional[str] = None,
        user: Optional[User] = None,
        token: Optional[str] = None,
    ) -> OTP:
        """
        Generate and send an OTP to a user via the specified delivery method.

        :param purpose: The purpose of the OTP.
        :type purpose: str
        :param delivery_method: The delivery method to send the OTP.
        :type delivery_method: str
        :param contact: The contact information (email or phone) to deliver the OTP to.
                        If not provided, it will be derived from the user.
        :type contact: str, optional
        :param user: The user associated with the OTP.
        :type user: User, optional
        :param token: Identity token, required for 2FA purposes.
        :type token: str, optional
        :raises ValidationError: If purpose or delivery method is invalid, or if required fields are missing.
        :raises Exception: If a contact cannot be determined.
        :return: The generated and stored OTP instance.
        :rtype: OTP
        """
        if delivery_method not in OTPDeliveryMethod.values:
            raise ValidationError('Invalid delivery method')

        if purpose not in OTPPurpose.values:
            raise ValidationError('Invalid purpose')

        identity = None
        if purpose == OTPPurpose.TWO_FACTOR_AUTHENTICATION:
            if not token:
                raise ValidationError('Please login again to proceed.')

            identity = Identity.objects.get(
                token=token,
                status=IdentityStatus.ACTIVATION_PENDING,
            )

            user = identity.user

        if not contact:
            if not user:
                raise ValidationError('Either contact or valid user must be provided.')


        system_settings = SystemSettingsCache.get()

        raw_code = cls._generate_raw_code(system_settings.otp_length)
        hashed_code = cls._hash_code(raw_code)

        expires_at = timezone.now() + timedelta(
            seconds=system_settings.otp_validity_seconds if purpose == OTPPurpose.TWO_FACTOR_AUTHENTICATION
            else system_settings.action_otp_validity_seconds
        )

        otp = OTP.objects.create(
            user=user,
            purpose=purpose,
            identity=identity,
            delivery_method=delivery_method,
            contact=contact,
            code=hashed_code,
            expires_at=expires_at
        )

        recipients = [contact] if contact else None

        NotificationServices.send_notification(
            user=user,
            notification_type=delivery_method,
            template_name=f'{delivery_method.lower()}_otp',
            recipients=recipients,
            context={'otp': raw_code},
        )

        return otp

    @classmethod
    def verify_otp(
        cls,
        purpose: str,
        code: str,
        contact: Optional[str] = None,
        user: Optional[User] = None,
        token: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Verify a provided OTP against the most recent unused OTP.

        :param purpose: The purpose of the OTP.
        :type purpose: str
        :param code: The OTP code entered by the user.
        :type code: str
        :param contact: The contact (email or phone) used to receive the OTP.
        :type contact: str, optional
        :param user: The user associated with the OTP.
        :type user: User, optional
        :param token: Identity token, required for 2FA verification.
        :type token: str, optional
        :raises ValidationError: If the OTP is invalid, expired, already used, or exceeds retry limits.
        :return: Optional data.
        :rtype: Optional[dict]
        """
        if not code:
            raise ValidationError('OTP code must be provided')

        if purpose not in OTPPurpose.values:
            raise ValidationError('Invalid purpose')

        identity = None
        if purpose == OTPPurpose.TWO_FACTOR_AUTHENTICATION:
            if not token:
                raise ValidationError('Token must be provided for 2FA purpose')

            identity = Identity.objects.get(
                token=token,
                status=IdentityStatus.ACTIVATION_PENDING
            )

        if not purpose == OTPPurpose.TWO_FACTOR_AUTHENTICATION:
            if not user and not contact:
                raise ValidationError('Either user_id or contact must be provided ')

        filter_params = {
            'is_used': False,
            'purpose': purpose
        }
        if user:
            filter_params['user'] = user
        if contact:
            filter_params['contact'] = contact
        if identity:
            filter_params['identity'] = identity

        otp_queryset = OTP.objects.filter(**filter_params)
        otp = otp_queryset.order_by('-created_at').first()
        if not otp:
            raise ValidationError('No valid OTP found. Please request a new OTP.')

        if otp.retry_count >= SystemSettingsCache.get().max_otp_attempts:
            raise ValidationError('Too many incorrect attempts. Please request a new OTP.')

        if cls._hash_code(code) != otp.code:
            otp.retry_count += 1
            otp.save()
            raise ValidationError('Incorrect OTP.')

        if otp.is_expired:
            raise ValidationError('OTP has expired. Please request a new OTP.')

        otp.is_used = True
        otp.save()

        if otp.identity:
            otp.identity.status = IdentityStatus.ACTIVE
            otp.identity.save(update_fields=['status'])
            otp.identity.extend()

            return {
                'identity_status': otp.identity.status,
                'user_profile': UserServices.get_user_profile(otp.identity.user.id),
            }


        return {}
