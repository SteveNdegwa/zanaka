import hashlib
import logging
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Union, Dict, Type

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from notifications.services.notification_types.base_notification import BaseNotification
from notifications.services.notification_types.email_notification import EmailNotification
from notifications.services.notification_types.sms_notification import SMSNotification
from notifications.services.providers.base_provider import BaseProvider
from notifications.services.providers.providers_registry import PROVIDER_CLASSES
from notifications.models import (
    NotificationFrequency,
    NotificationType,
    NotificationStatus,
    Provider,
    Notification,
    Template
)
from users.models import User, StudentGuardian, RoleName

logger = logging.getLogger(__name__)


class NotificationServices:
    """
    Service class responsible for preparing, validating, scheduling, and sending notifications.
    """

    NOTIFICATION_HANDLERS: Dict[str, Type[BaseNotification]] = {
        "EMAIL": EmailNotification,
        "SMS": SMSNotification,
    }

    @classmethod
    def _generate_unique_key(cls, user: User, key: str, frequency: str) -> str:
        """
        Generates a unique SHA-256 hash used for deduplication of notifications
        based on the user, key, and selected frequency window.

        :param user: The user associated with the notification.
        :type user: User
        :param key: Identifier used to deduplicate similar notifications.
        :type key: str
        :param frequency: Frequency constraint for deduplication.
        :type frequency: str
        :return: A hashed unique key string.
        :rtype: str
        """
        now = datetime.now()
        if frequency == NotificationFrequency.MONTHLY:
            key_str = f"{user.id}_{key}_{now.year}_{now.month}"
        elif frequency == NotificationFrequency.WEEKLY:
            y, w, _ = now.isocalendar()
            key_str = f"{user.id}_{key}_{y}_{w}"
        elif frequency == NotificationFrequency.DAILY:
            key_str = f"{user.id}_{key}_{now.date()}"
        else:
            key_str = f"{user.id}_{key}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    @classmethod
    def _get_deduplication_window(cls, frequency: str) -> Optional[timedelta]:
        """
        Returns a time window used to check for duplicate notifications.

        :param frequency: Notification frequency.
        :type frequency: str
        :return: A timedelta window or None if unrestricted.
        :rtype: Optional[timedelta]
        """
        if frequency == NotificationFrequency.MONTHLY:
            return timedelta(days=31)
        elif frequency == NotificationFrequency.WEEKLY:
            return timedelta(days=7)
        elif frequency == NotificationFrequency.DAILY:
            return timedelta(hours=24)
        else:
            return None

    @classmethod
    def _is_duplicate(cls, user: User, unique_key: str, frequency: str) -> bool:
        """
        Determines whether an equivalent notification already exists within the
        relevant deduplication window.

        :param user: The user receiving the notification.
        :type user: User
        :param unique_key: Hashed deduplication key.
        :type unique_key: str
        :param frequency: Notification frequency.
        :type frequency: str
        :return: True if a duplicate exists, False otherwise.
        :rtype: bool
        """
        window = cls._get_deduplication_window(frequency)
        if window is None:
            return Notification.objects.filter(
                user=user,
                unique_key=unique_key
            ).exists()
        return Notification.objects.filter(
            user=user,
            unique_key=unique_key,
            created_at__gte=datetime.now() - window
        ).exists()

    @classmethod
    def _clean_recipients(cls, notification_type: str, recipients: Union[List[str], str]) -> List[str]:
        """
        Sanitizes and normalizes recipient values by trimming whitespace,
        removing invalid entries, and formatting values where required.

        :param notification_type: Type of notification ("email" or "sms").
        :type notification_type: str
        :param recipients: A list or comma-separated string of recipients.
        :type recipients: Union[List[str], str]
        :return: A cleaned, deduplicated list of recipients.
        :rtype: List[str]
        """
        cleaned_recipients = set()
        if isinstance(recipients, str):
            recipients = [recipient for recipient in recipients.split(",")]
        for recipient in recipients:
            recipient = recipient.strip()
            if not recipient:
                continue
            if notification_type == "sms":
                recipient = recipient.replace("+", "")
            cleaned_recipients.add(recipient)
        return list(cleaned_recipients)

    @classmethod
    def _get_notification_handler_instance(cls, notification) -> BaseNotification:
        """
        Returns a notification handler class instance based on the notification type.

        :param notification: Notification object instance.
        :type notification: Notification
        :return: An instantiated notification handler.
        :rtype: BaseNotification
        :raises ValueError: If notification type is unsupported.
        """
        notification_type_name = notification.notification_type
        notification_class = cls.NOTIFICATION_HANDLERS.get(notification_type_name)
        if not notification_class:
            raise ValueError(f"Unsupported notification type: {notification_type_name}")
        return notification_class(notification)

    @classmethod
    def _get_provider_class_instance(cls, provider: Provider) -> BaseProvider:
        """
        Returns a provider instance based on the provider's configured class name.

        :param provider: Provider model instance.
        :type provider: Provider
        :return: Instantiated provider class.
        :rtype: BaseProvider
        :raises ValueError: If provider class is unknown.
        """
        provider_class = PROVIDER_CLASSES.get(provider.class_name, None)
        if provider_class is None:
            raise ValueError(f"Unknown provider class: {provider.class_name}")
        return provider_class(provider.config)

    @classmethod
    def deliver_notification(cls, notification_id: str) -> None:
        """
        Delivers a notification by preparing content, validating providers,
        sending through active providers, and updating notification status.

        :param notification_id: The ID of the notification to deliver.
        :type notification_id: str
        :raises Exception: If sending fails or no active providers are available.
        :rtype: None
        """
        notification = None
        try:
            notification = Notification.objects.get(id=notification_id)

            notification_handler = cls._get_notification_handler_instance(notification)
            notification_handler.validate()

            active_providers = notification_handler.active_providers()
            if not active_providers.exists():
                raise Exception(
                    f"No active providers found for {notification.notification_type.name} notifications"
                )

            content = notification_handler.prepare_content()

            for provider in active_providers:
                provider_class_instance = cls._get_provider_class_instance(provider)

                if not provider_class_instance.validate_config():
                    logger.warning(f"Invalid configuration for provider: {provider.name}")
                    continue

                send_notification_state = provider_class_instance.send(
                    recipients=notification.recipients,
                    content=content
                )

                if send_notification_state == NotificationStatus.FAILED:
                    logger.warning(f"Send notification failed for provider: {provider.name}")
                    continue

                notification.status = send_notification_state
                notification.provider = provider
                if send_notification_state == NotificationStatus.SENT:
                    notification.sent_time = timezone.now()
                notification.save()

                return None

            raise Exception("Notification not sent")

        except Exception as ex:
            logger.exception(f"NotificationManagementService - _send_notification exception: {ex}")
            if notification:
                notification.status = NotificationStatus.FAILED
                notification.failure_message = str(ex)
                notification.failure_traceback = traceback.format_exc()
                notification.save()
            raise

    @classmethod
    def send_notification(
            cls,
            user: Optional[User] = None,
            recipients: Optional[List[str]] = None,
            notification_type: str = NotificationType.EMAIL,
            template_name: str = "default_email",
            context: Optional[dict] = None,
            notification_key: Optional[str] = None,
            frequency: str = NotificationFrequency.ONCE,
    ) -> None:
        """
        Creates, validates, and dispatches a notification, optionally applying
        deduplication rules based on frequency.

        :param user: User receiving the notification (optional).
        :type user: Optional[User]
        :param recipients: Explicit list of recipients if user is not provided.
        :type recipients: Optional[List[str]]
        :param notification_type: Notification type ("email" or "sms").
        :type notification_type: str
        :param template_name: The template name to render.
        :type template_name: str
        :param context: Template context variables.
        :type context: Optional[dict]
        :param notification_key: Identifier for deduplication.
        :type notification_key: Optional[str]
        :param frequency: Deduplication frequency constraint.
        :type frequency: str
        :raises ValidationError: For invalid inputs or missing recipients.
        :rtype: None
        """
        # Input validation
        notification_type = notification_type.lower()
        if notification_type not in NotificationType.values:
            raise ValidationError("Invalid notification type")

        frequency = frequency.lower()
        if frequency not in NotificationFrequency.values:
            raise ValidationError("Invalid notification frequency")

        if not user and not recipients:
            raise ValidationError("Either user or recipients must be provided.")

        # Check for duplicate notifications
        unique_key = None
        if notification_key and user:
            unique_key = cls._generate_unique_key(
                user=user,
                key=notification_key,
                frequency=frequency
            )
            is_duplicate = cls._is_duplicate(
                user=user,
                unique_key=unique_key,
                frequency=frequency
            )
            if is_duplicate:
                return None

        # If user is provided, determine recipients based on notification type
        if user:
            field = "email" if notification_type == NotificationType.EMAIL else "phone_number"
            if not user.role.name == RoleName.STUDENT:
                profile = getattr(user, f"{user.role.name}_profile")
                recipients = [getattr(profile, field)]
            else:
                qs = StudentGuardian.objects.filter(
                    student=user,
                    is_active=True,
                    can_receive_reports=True
                ).select_related( "guardian")
                recipients = [getattr(sg.guardian, field) for sg in qs]

        # Clean recipients list
        recipients = cls._clean_recipients(
            recipients=recipients,
            notification_type=notification_type
        )
        if not recipients:
            raise ValidationError("No valid recipients found.")

        # Validate template
        template = Template.objects.filter(
            name=template_name,
            notification_type=notification_type,
            is_active=True
        ).first()
        if not template:
            return None

        # Create notification
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            template=template,
            recipients=recipients,
            context=context or {},
            frequency=frequency,
            unique_key=unique_key
        )

        # Deliver notification
        if settings.SEND_NOTIFICATIONS_ASYNC:
            from notifications.tasks import deliver_notification_task
            deliver_notification_task.delay(notification.id)
        else:
            cls.deliver_notification(notification.id)

        return None
