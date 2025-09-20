import logging

from django.utils import timezone

from authentication.models import Identity
from users.models import Device, User

logger = logging.getLogger(__name__)


class DeviceService:
    @classmethod
    def create_device(cls, user_id: str, device_token: str) -> Device:
        user = User.objects.get(id=user_id, is_active=True)

        device = Device.objects.filter(token=device_token).first()
        if device:
            if device.user != user:
                if device.is_active:
                    previous_user = device.user
                    previous_user.is_verified = False
                    previous_user.save()

                    Identity.objects.filter(
                        user=previous_user,
                        device=device,
                        status=Identity.Status.ACTIVE
                    ).update(status=Identity.Status.EXPIRED)

                user.is_verified = False
                user.save()

                device.user = user

            device.is_active = True
            device.last_activity = timezone.now()
            device.save()

        else:
            device = Device.objects.create(
                user=user,
                token=device_token,
                last_activity=timezone.now(),
                is_active=True
            )

            user.is_verified = False
            user.save()

        Device.objects.filter(
            user=user, is_active=True
        ).exclude(id=device.id).update(is_active=False)

        Identity.objects.filter(
            user=user,
            status=Identity.Status.ACTIVE
        ).exclude(device=device).update(status=Identity.Status.EXPIRED)

        return device

    @classmethod
    def deactivate_device(cls, device_id: str) -> Device:
        device = Device.objects.get(id=device_id)
        if device.is_active:
            Identity.objects.filter(
                device=device, status=Identity.Status.ACTIVE
            ).update(status=Identity.Status.EXPIRED)

            device.is_active = False
            device.save()

        return device
