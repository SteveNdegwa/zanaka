from django.http import JsonResponse

from notifications.models import Notification, NotificationStatus
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider


def belio_sms_provider_callback(request: ExtendedRequest) -> JsonResponse:
    delivery_status = request.data.get('deliveryStatus', '')
    notification_id = request.data.get('correlator', '')
    sent_time = request.data.get('timestamp', '')

    notification = Notification.objects.get(id=notification_id)

    if delivery_status == 'DeliveredToTerminal':
        notification.status = NotificationStatus.SENT
        notification.sent_time = sent_time
    else:
        notification.status = NotificationStatus.FAILED
        notification.sent_time = None

    notification.save()

    return ResponseProvider.success()
