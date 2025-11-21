import hashlib
from datetime import timedelta
from random import randint
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from authentication.models import Identity
from base.services.base_services import BaseServices
from notifications.services.notification_services import NotificationServices
from otps.models import OTP
from users.models import User


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
        if delivery_method not in OTP.DeliveryMethods.values:
            raise ValidationError('Invalid delivery method')

        if purpose not in OTP.PurposeTypes.values:
            raise ValidationError('Invalid purpose')

        identity = None
        if purpose == OTP.PurposeTypes.TWO_FACTOR_AUTHENTICATION:
            if not token:
                raise ValidationError('Token must be provided for 2FA purpose')

            identity = Identity.objects.get(
                token=token,
                status=Identity.Status.ACTIVATION_PENDING,
            )

            user = identity.user

        if not contact:
            if not user:
                raise ValidationError('Either contact or valid user must be provided.')
            contact = user.email if delivery_method == 'EMAIL' else user.phone_number
            if not contact:
                raise Exception('Contact not found')

        raw_code = cls._generate_raw_code(settings.OTP_LENGTH)
        hashed_code = cls._hash_code(raw_code)

        expires_at = timezone.now() + timedelta(
            seconds=settings.OTP_VALIDITY_SECONDS if purpose == OTP.PurposeTypes.TWO_FACTOR_AUTHENTICATION
            else settings.ACTION_OTP_VALIDITY_SECONDS
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
            template_name=f'{delivery_method}_otp',
            recipients=recipients,
            context={'otp': raw_code},
        )

        return otp

    @classmethod
    @transaction.atomic
    def verify_otp(
        cls,
        purpose: str,
        code: str,
        contact: Optional[str] = None,
        user: Optional[User] = None,
        token: Optional[str] = None,
    ) -> OTP:
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
        :return: The verified OTP instance with updated status.
        :rtype: OTP
        """
        if not code:
            raise ValidationError('OTP code must be provided')

        if purpose not in OTP.PurposeTypes.values:
            raise ValidationError('Invalid purpose')

        identity = None
        if purpose == OTP.PurposeTypes.TWO_FACTOR_AUTHENTICATION:
            if not token:
                raise ValidationError('Token must be provided for 2FA purpose')

            identity = Identity.objects.get(
                token=token,
                status=Identity.Status.ACTIVATION_PENDING
            )

        if not purpose == OTP.PurposeTypes.TWO_FACTOR_AUTHENTICATION:
            if not user and not contact:
                raise ValidationError('Either user_id or contact must be provided ')

        filter_params = {
            'is_used': False,
            'expires_at__gte': timezone.now(),
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
            raise ValidationError('No valid OTP found.')

        if otp.retry_count >= settings.OTP_MAX_RETRIES:
            raise ValidationError('Too many incorrect attempts. Please request a new OTP.')

        if cls._hash_code(code) != otp.code:
            otp.retry_count += 1
            otp.save()
            raise ValidationError('Incorrect OTP.')

        if otp.identity:
            otp.identity.status = Identity.Status.ACTIVE
            otp.identity.extend()

        otp.is_used = True
        otp.save()

        return otp
