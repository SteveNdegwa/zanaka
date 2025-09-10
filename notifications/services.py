from notifications.models import Notification
from utils.service_base import ServiceBase


class NotificationService(ServiceBase[Notification]):
    manager = Notification.objects