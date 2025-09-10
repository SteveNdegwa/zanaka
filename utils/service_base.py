import logging
from typing import Optional, Any, Dict, Union, List, TypeVar, Generic, Type
from django.db import models, transaction
from django.db.models import QuerySet
from django.core.exceptions import ValidationError, ObjectDoesNotExist, MultipleObjectsReturned

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=models.Model)


class ServiceBase(Generic[T]):
    """
    Base service class to handle CRUD operations with improved error handling,
    performance optimizations, and better type safety.
    """

    manager: Optional[models.Manager] = None

    def __init__(self, lock_for_update: bool = False, **annotations):
        """
        Initializes the service with optional locking and annotations.

        :param lock_for_update: Whether to use `select_for_update()` for the queryset.
        :param annotations: Annotations to apply to the manager queryset.
        :raises ValueError: If manager is not properly configured.
        """
        if self.manager is None:
            raise ValueError(
                f'{self.__class__.__name__} must define a "manager" class attribute'
            )

        self._queryset = self.manager.all()

        try:
            if lock_for_update:
                self._queryset = self._queryset.select_for_update()
            if annotations:
                self._queryset = self._queryset.annotate(**annotations)
        except Exception as ex:
            logger.error(
                'Failed to initialize %s with annotations or lock: %s',
                self.__class__.__name__, ex
            )
            raise

    @property
    def model(self) -> Type[T]:
        """
        Get the model class associated with this service.
        """
        return self.manager.model

    def get(self, *args, **kwargs) -> Optional[T]:
        """
        Get a single record from the database.

        :return: Model instance or None if not found.
        :raises MultipleObjectsReturned: If multiple objects are returned.
        """
        try:
            return self._queryset.get(*args, **kwargs)
        except ObjectDoesNotExist:
            logger.debug(
                '%s.get() - Object not found with args=%s, kwargs=%s',
                self.model.__name__, args, kwargs
            )
            return None
        except MultipleObjectsReturned as e:
            logger.error(
                '%s.get() - Multiple objects returned: %s',
                self.model.__name__, e
            )
            raise
        except Exception as e:
            logger.exception(
                '%s.get() - Unexpected error: %s',
                self.model.__name__, e
            )
            return None

    def filter(self, *args, **kwargs) -> Optional[QuerySet]:
        """
        Return a queryset of filtered records.

        :return: QuerySet or None if error occurs.
        """
        try:
            return self._queryset.filter(*args, **kwargs)
        except Exception as e:
            logger.exception(
                '%s.filter() - Filter error: %s',
                self.model.__name__, e
            )
            return None

    def all(self) -> Optional[QuerySet]:
        """
        Return all records.

        :return: QuerySet or None if error occurs.
        """
        try:
            return self._queryset.all()
        except Exception as e:
            logger.exception(
                '%s.all() - Error retrieving all records: %s',
                self.model.__name__, e
            )
            return None

    def exists(self, *args, **kwargs) -> bool:
        """
        Check if records exist with given filters.

        :return: True if records exist, False otherwise.
        """
        try:
            return self._queryset.filter(*args, **kwargs).exists()
        except Exception as e:
            logger.exception(
                '%s.exists() - Error checking existence: %s',
                self.model.__name__, e
            )
            return False

    def count(self, *args, **kwargs) -> int:
        """
        Count records with given filters.

        :return: Number of records, 0 if error occurs.
        """
        try:
            if args or kwargs:
                return self._queryset.filter(*args, **kwargs).count()
            return self._queryset.count()
        except Exception as e:
            logger.exception(
                '%s.count() - Error counting records: %s',
                self.model.__name__, e
            )
            return 0

    @transaction.atomic
    def create(self, **kwargs) -> Optional[T]:
        """
        Create a new record with given attributes.

        :param kwargs: Field values for the new record.
        :return: The created object or None if creation fails.
        """
        try:
            self._validate_fields(kwargs)
            instance = self.manager.create(**kwargs)
            return instance
        except ValidationError as e:
            logger.error(
                '%s.create() - Validation error: %s',
                self.model.__name__, e
            )
        except Exception as e:
            logger.exception(
                '%s.create() - Creation error: %s',
                self.model.__name__, e
            )
        return None

    @transaction.atomic
    def update(self, pk: Any, **kwargs) -> Optional[T]:
        """
        Update a record by its primary key.

        :param pk: Primary key of the record.
        :param kwargs: Fields to update.
        :return: Updated object or None if update fails.
        """
        try:
            record = self.get(pk=pk)
            if record is None:
                logger.warning(
                    '%s.update() - Record with pk=%s not found',
                    self.model.__name__, pk
                )
                return None

            valid_kwargs = self._filter_valid_fields(kwargs)
            if not valid_kwargs:
                logger.warning(
                    '%s.update() - No valid fields to update',
                    self.model.__name__
                )
                return record

            updated = False
            for field, value in valid_kwargs.items():
                current_value = getattr(record, field)
                if current_value != value:
                    setattr(record, field, value)
                    updated = True

            if not updated:
                logger.debug(
                    '%s.update() - No changes detected for pk=%s',
                    self.model.__name__, pk
                )
                return record

            if hasattr(record, 'SYNC_MODEL') and getattr(record, 'SYNC_MODEL', False):
                if hasattr(record, 'synced'):
                    record.synced = False

            record.full_clean()
            record.save(
                update_fields=list(valid_kwargs.keys()) + (['synced'] if hasattr(record, 'synced') else [])
            )

            return record

        except ValidationError as e:
            logger.error(
                '%s.update() - Validation error for pk=%s: %s',
                self.model.__name__, pk, e
            )
        except Exception as e:
            logger.exception(
                '%s.update() - Update error for pk=%s: %s',
                self.model.__name__, pk, e
            )
        return None

    @transaction.atomic
    def delete(self, pk: Any) -> bool:
        """
        Delete a record by its primary key.

        :param pk: Primary key of the record to delete.
        :return: True if deletion was successful, False otherwise.
        """
        try:
            record = self.get(pk=pk)
            if record is None:
                logger.warning(
                    '%s.delete() - Record with pk=%s not found',
                    self.model.__name__, pk
                )
                return False

            record.delete()
            return True

        except Exception as e:
            logger.exception(
                '%s.delete() - Deletion error for pk=%s: %s',
                self.model.__name__, pk, e
            )
            return False

    @transaction.atomic
    def get_or_create(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[Optional[T], bool]:
        """
        Get an object, or create one if it doesn't exist.
        """
        try:
            if kwargs:
                self._validate_fields(kwargs)

            if defaults:
                self._validate_fields(defaults)

            obj, created = self.manager.get_or_create(defaults=defaults, **kwargs)

            return obj, created

        except ValidationError as e:
            logger.error(
                '%s.get_or_create() - Validation error: %s',
                self.model.__name__, e
            )
        except Exception as e:
            logger.exception(
                '%s.get_or_create() - Error: %s',
                self.model.__name__, e
            )
        return None, False

    @transaction.atomic
    def update_or_create(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[Optional[T], bool]:
        """
        Update an object with the given kwargs, creating a new one if necessary.
        """
        try:
            if kwargs:
                self._validate_fields(kwargs)

            if defaults:
                self._validate_fields(defaults)

            obj, created = self.manager.update_or_create(defaults=defaults, **kwargs)

            if not created and hasattr(obj, 'SYNC_MODEL') and getattr(obj, 'SYNC_MODEL', False):
                if hasattr(obj, 'synced'):
                    obj.synced = False
                    obj.save(update_fields=['synced'])

            return obj, created

        except ValidationError as e:
            logger.error(
                '%s.update_or_create() - Validation error: %s',
                self.model.__name__, e
            )
        except Exception as e:
            logger.exception(
                '%s.update_or_create() - Error: %s',
                self.model.__name__, e
            )
        return None, False

    @transaction.atomic
    def bulk_create(
        self,
        objects: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False
    ) -> List[T]:
        """
        Create multiple records in a single database query.
        """
        try:
            instances = []
            for obj_data in objects:
                self._validate_fields(obj_data)
                instances.append(self.model(**obj_data))

            created_objects = self.model.objects.bulk_create(
                instances,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts
            )

            return created_objects

        except Exception as e:
            logger.exception(
                '%s.bulk_create() - Error creating objects: %s',
                self.model.__name__, e
            )
            return []

    def bulk_update(self, objs: List[T], fields: List[str], batch_size: Optional[int] = None) -> int:
        """
        Update multiple objects in a single database query.
        """
        try:
            valid_fields = self._get_valid_field_names()
            invalid_fields = set(fields) - valid_fields
            if invalid_fields:
                raise ValidationError(
                    f'Invalid fields for bulk update: {invalid_fields}'
                )

            sync_objs = []
            for obj in objs:
                if hasattr(obj, 'SYNC_MODEL') and getattr(obj, 'SYNC_MODEL', False):
                    if hasattr(obj, 'synced'):
                        obj.synced = False
                        sync_objs.append(obj)

            update_fields = fields.copy()
            if sync_objs and 'synced' not in update_fields:
                update_fields.append('synced')

            updated_count = self.manager.bulk_update(
                objs, update_fields, batch_size=batch_size
            )

            return updated_count

        except Exception as e:
            logger.exception(
                '%s.bulk_update() - Error updating objects: %s',
                self.model.__name__, e
            )
            return 0

    def _validate_fields(self, field_data: Dict[str, Any]) -> None:
        """
        Validate field data against model fields.
        """
        valid_fields = self._get_valid_field_names()
        invalid_fields = set(field_data.keys()) - valid_fields

        if invalid_fields:
            raise ValidationError(
                f'Invalid fields for {self.model.__name__}: {invalid_fields}'
            )

    def _filter_valid_fields(self, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out invalid fields from the provided data.
        """
        valid_fields = self._get_valid_field_names()
        return {k: v for k, v in field_data.items() if k in valid_fields}

    def _get_valid_field_names(self) -> set:
        """
        Get set of valid field names for the model.
        """
        return {
            field.name for field in self.model._meta.get_fields()
            if field.concrete and not field.auto_created
        }
