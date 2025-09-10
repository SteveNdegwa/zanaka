from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import GenericBaseModel


class School(GenericBaseModel):
    code = models.CharField(max_length=10, unique=True, verbose_name=_('Code'))
    address = models.TextField(blank=True, null=True, verbose_name=_('Address'))
    contact_email = models.EmailField(blank=True, null=True, verbose_name=_('Contact Email'))
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Contact Phone'))
    established_date = models.DateField(blank=True, null=True, verbose_name=_('Established Date'))

    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ('name',)


class Branch(GenericBaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        UNDER_CONSTRUCTION = 'under_construction', _('Under Construction')

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name=_('School')
    )
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Location'))
    contact_email = models.EmailField(blank=True, null=True, verbose_name=_('Contact Email'))
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Contact Phone'))
    principal = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches',
        verbose_name=_('Principal')
    )
    capacity = models.PositiveIntegerField(default=0, verbose_name=_('Student Capacity'))
    established_date = models.DateField(blank=True, null=True, verbose_name=_('Established Date'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_('Status')
    )
    website = models.URLField(blank=True, null=True, verbose_name=_('Website'))

    class Meta:
        verbose_name = _('Branch')
        verbose_name_plural = _('Branches')
        unique_together = ('school', 'name')
        ordering = ('name', '-date_created')

    def __str__(self):
        return f'{self.name} ({self.school.name})'


class Classroom(GenericBaseModel):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name=_('Branch')
    )
    capacity = models.PositiveIntegerField(default=0, verbose_name=_('Student Capacity'))

    class Meta:
        verbose_name = _('Classroom')
        verbose_name_plural = _('Classrooms')
        unique_together = ('branch', 'name')
        ordering = ('name', '-date_created')

    def __str__(self):
        return f'{self.name} ({self.branch.name})'
