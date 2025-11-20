import logging

from celery import shared_task

from notifications.services.notification_services import NotificationManagementService

logger = logging.getLogger(__name__)


@shared_task(name='deliver_notification_task')
def deliver_notification_task(notification_id: str) -> str:
    try:
        NotificationManagementService.deliver_notification(notification_id)
        return "success"
    except Exception as ex:
        logger.exception("CeleryTasks - send_notification exception: %s" % ex)
        return "failed"
