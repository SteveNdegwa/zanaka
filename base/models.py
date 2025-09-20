import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from audit.mixins import AuditableMixin
from base.managers import PrimaryDBManager


class BaseModel(AuditableMixin, models.Model):
    id = models.UUIDField(
        max_length=100,
        default=uuid.uuid4,
        unique=True,
        editable=False,
        primary_key=True,
        verbose_name=_("Unique identifier")
    )
    date_modified = models.DateTimeField(auto_now=True, verbose_name=_("Date modified"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    synced = models.BooleanField(
        default=False,
        verbose_name=_("Synced"),
        help_text=_("Indicates whether this record has been synchronized with the replica system.")
    )

    # objects = PrimaryDBManager()
    objects = models.Manager()

    class Meta(object):
        abstract = True


class GenericBaseModel(BaseModel):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    description = models.CharField(max_length=100, blank=True, verbose_name=_("Description"))

    class Meta(object):
        abstract = True