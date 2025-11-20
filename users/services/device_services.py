from django.utils import timezone

from authentication.models import Identity
from base.services.base_services import BaseServices
from users.models import User, Device


class DeviceServices(BaseServices):
    @classmethod
    def add_device(cls, user: User, device_token: str) -> Device:
        """
        Add or activate a device for a user, updating Identity statuses.

        :param user: User instance.
        :param device_token: Unique token for the device.
        :rtype: Device
        """
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
    def remove_device(cls, device_id: str) -> Device:
        """
        Deactivate a device and expire associated active Identities.

        :param device_id: ID of the device to remove.
        :rtype: Device
        """
        device = Device.objects.get(id=device_id)
        if device.is_active:
            Identity.objects.filter(
                device=device, status=Identity.Status.ACTIVE
            ).update(status=Identity.Status.EXPIRED)
            device.is_active = False
            device.save(update_fields=["is_active"])
        return device
