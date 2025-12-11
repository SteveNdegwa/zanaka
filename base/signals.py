from django.db.models.signals import post_save
from django.dispatch import receiver
from base.models import SystemSettings
from base.services.system_settings_cache import SystemSettingsCache


@receiver(post_save, sender=SystemSettings)
def refresh_system_settings_cache(sender, instance, **kwargs) -> None:
    SystemSettingsCache.refresh()
