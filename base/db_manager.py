import logging
from django.db import connections, transaction
from django.apps import apps

logger = logging.getLogger(__name__)


class DBManager:
    PRIMARY_ALIAS = "default"
    REPLICA_ALIAS = "replica"
    _current_primary = "default"
    _current_replica = "replica"

    @classmethod
    def promote_replica(cls):
        logger.warning("Promoting replica to primary...")
        cls._PRIMARY_ALIAS, cls._REPLICA_ALIAS = cls.REPLICA_ALIAS, cls.PRIMARY_ALIAS
        logger.info(f"Replica promoted. New primary: {cls._PRIMARY_ALIAS}")

    @classmethod
    def reintegrate_old_primary(cls):
        logger.warning("Reintegrating old primary as replica...")

        primary_conn = connections[cls._PRIMARY_ALIAS]
        replica_conn = connections[cls._REPLICA_ALIAS]

        for model in apps.get_models():
            if not hasattr(model, "synced"):
                continue

            primary_qs = model.objects.using(cls._PRIMARY_ALIAS).filter(synced=False)
            for obj in primary_qs.iterator():
                obj.save(using=cls._REPLICA_ALIAS)
                model.objects.using(cls._PRIMARY_ALIAS).filter(pk=obj.pk).update(synced=True)

        logger.info("Old primary reintegrated as replica and resynced.")
