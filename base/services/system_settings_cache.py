from threading import Lock
from base.models import SystemSettings

class SystemSettingsCache:
    """
    Thread-safe cache for the singleton SystemSettings instance.

    This class provides efficient access to the SystemSettings object,
    ensuring that the database is queried only once per process.
    """

    _instance = None
    _lock = Lock()

    @classmethod
    def get(cls) -> SystemSettings:
        """
        Retrieve the cached SystemSettings instance.

        If the cache is empty, the SystemSettings singleton is loaded from
        the database in a thread-safe manner and stored for subsequent calls.

        :return: Cached SystemSettings instance.
        :rtype: SystemSettings
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SystemSettings.get_solo()
        return cls._instance

    @classmethod
    def refresh(cls) -> None:
        """
        Refresh the cached SystemSettings instance from the database.

        This method forcibly reloads the SystemSettings singleton.
        Called from a post_save signal after SystemSettings are updated.

        :return: None
        """
        with cls._lock:
            cls._instance = SystemSettings.get_solo()
