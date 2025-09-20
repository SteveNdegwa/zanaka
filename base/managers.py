from django.db import models
from base.db_manager import DBManager


class PrimaryDBManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().using(DBManager.PRIMARY_ALIAS)

    def create(self, **kwargs):
        return self.get_queryset().create(**kwargs)

    def get_or_create(self, **kwargs):
        return self.get_queryset().get_or_create(**kwargs)

    def update_or_create(self, **kwargs):
        return self.get_queryset().update_or_create(**kwargs)

    def bulk_create(self, objs, **kwargs):
        return self.get_queryset().bulk_create(objs, **kwargs)

    def bulk_update(self, objs, fields, **kwargs):
        return self.get_queryset().bulk_update(objs, fields, **kwargs)

