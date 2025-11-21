from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import GenericBaseModel


class GradeLevel(models.TextChoices):
    BABY_CLASS = 'baby_class', _('Baby Class')
    PP_1 = 'pp_1', _('PP 1')
    PP_2 = 'pp_2', _('PP 2')
    GRADE_1 = 'grade_1', _('Grade 1')
    GRADE_2 = 'grade_2', _('Grade 2')
    GRADE_3 = 'grade_3', _('Grade 3')
    GRADE_4 = 'grade_4', _('Grade 4')
    GRADE_5 = 'grade_5', _('Grade 5')
    GRADE_6 = 'grade_6', _('Grade 6')
    GRADE_7 = 'grade_7', _('Grade 7')
    GRADE_8 = 'grade_8', _('Grade 8')
    GRADE_9 = 'grade_9', _('Grade 9')


class School(GenericBaseModel):
    code = models.CharField(max_length=10, unique=True, verbose_name=_('Code'))
    address = models.TextField(blank=True, null=True, verbose_name=_('Address'))
    contact_email = models.EmailField(blank=True, null=True, verbose_name=_('Contact Email'))
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Contact Phone'))
    established_date = models.DateField(blank=True, null=True, verbose_name=_('Established Date'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ('name',)


class Branch(GenericBaseModel):
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
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('Branch')
        verbose_name_plural = _('Branches')
        unique_together = ('school', 'name')
        ordering = ('name', '-created_at')

    def __str__(self):
        return f'{self.name} ({self.school.name})'


class Classroom(GenericBaseModel):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='classrooms',
        verbose_name=_('Branch')
    )
    grade_level = models.CharField(max_length=10, choices=GradeLevel.choices, verbose_name=_('Grade Level'))
    capacity = models.PositiveIntegerField(default=0, verbose_name=_('Student Capacity'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('Classroom')
        verbose_name_plural = _('Classrooms')
        unique_together = ('branch', 'name')
        ordering = ('name', '-created_at')

    def __str__(self):
        return f'{self.name} ({self.branch.name})'
