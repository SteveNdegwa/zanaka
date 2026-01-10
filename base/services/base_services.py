import uuid

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class BaseServices:
    """
    Base service class for service-layer operations.
    """

    fk_mappings: dict[str, tuple[str, str]] = {}
    """
    Mapping of input field names to tuples of (model_path, resolved_field).
    Example: {'school_id': ('app_label.School', 'school')}
    Specified in each child class if needed.
    """

    @classmethod
    def _sanitize_and_validate_data(
        cls,
        data: dict,
        required_fields: set[str] | None = None,
        allowed_fields: set[str] | None = None,
        field_types: dict[str, type] | None = None,
        resolve_foreign_keys: bool = True
    ) -> dict:
        """
        Clean and validate input data.

        Operations performed:
          - Strips whitespace from strings.
          - Converts empty strings to `None`.
          - Keeps only allowed fields if 'allowed_fields' is specified.
          - Validates that all required fields are present and non-empty.
          - Type-casts values based on 'field_types' if provided.
          - Resolves foreign key IDs into model instances using 'fk_mappings'.

        :param data: Dictionary of raw input data.
        :type data: dict
        :param required_fields: Set of required fields that must be present and non-empty.
        :type required_fields: set[str] | None
        :param allowed_fields: Set of fields that are allowed in the input. Others are ignored.
        :type allowed_fields: set[str] | None
        :param field_types: Mapping of field names to expected types for type-casting.
        :type field_types: dict[str, type] | None
        :param resolve_foreign_keys: Whether to resolve foreign key IDs into model instances.
        :type resolve_foreign_keys: bool
        :raises ValidationError: If required fields are missing or type casting fails.
        :return: Sanitized and validated dictionary.
        :rtype: dict
        """
        cleaned = {}

        for k, v in data.items():
            # Skip disallowed keys
            if allowed_fields and k not in allowed_fields:
                continue

            # Normalize strings
            if isinstance(v, str):
                v = v.strip()
                if v == '':
                    v = None

            # Apply type casting if specified
            if field_types and k in field_types and v is not None:
                try:
                    v = field_types[k](v)
                except (ValueError, TypeError):
                    raise ValidationError(f'Invalid type for {k}, expected {field_types[k].__name__}')

            cleaned[k] = v

        # Validate required fields
        if required_fields:
            missing = [f for f in required_fields if not cleaned.get(f)]
            if missing:
                raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        # Resolve foreign keys
        if resolve_foreign_keys:
            cleaned = cls._resolve_foreign_keys(cleaned)

        return cleaned

    @classmethod
    def _resolve_foreign_keys(cls, data: dict) -> dict:
        """
        Resolve foreign key IDs in the input data into actual model instances.

        Uses 'fk_mappings' defined in the child service to map input fields
        (like 'school_id') into actual model instances ('School' object).

        :param data: Dictionary containing input data, possibly including foreign key IDs.
        :type data: dict
        :raises ValidationError: If a referenced foreign key object does not exist or is inactive.
        :return: Dictionary with foreign key fields replaced by model instances.
        :rtype: dict
        """
        resolved = {}

        if not cls.fk_mappings:
            return data

        for field, value in data.items():
            if field in cls.fk_mappings and value:
                model_path, attr = cls.fk_mappings[field]
                model = apps.get_model(model_path)

                try:
                    val_uuid = uuid.UUID(str(value))
                    try:
                        if "is_active" in [f.name for f in model._meta.get_fields()]:
                            resolved[attr] = model.objects.get(id=val_uuid, is_active=True)
                        else:
                            resolved[attr] = model.objects.get(id=val_uuid)
                    except ObjectDoesNotExist:
                        raise ValidationError(f'{attr} with id={value} does not exist or is inactive.')
                except ValueError:
                    try:
                        resolved[attr] = model.objects.get(name=value, is_active=True)
                    except ObjectDoesNotExist:
                        raise ValidationError(f'{attr} with name={value} does not exist or is inactive.')
            else:
                resolved[field] = value

        return resolved

    @classmethod
    def _validate_model_uniqueness(
            cls,
            model,
            data: dict,
            *,
            unique_fields: set[str] = None,
            ignore_fields: set[str] = None,
            exclude_instance=None,
            self_scope: dict | None = None,
    ) -> None:
        """
        Validate that the specified fields in a model are unique, with support for
        additional filtering, exclusion, and related object scoping.

        :param model: The Django model class to validate uniqueness on.
        :type model: models.Model
        :param data: Dictionary of field names and their values to check for uniqueness.
        :type data: dict
        :param unique_fields: Set of field names to enforce uniqueness. Defaults to all  unique fields on the model.
        :type unique_fields: set[str], optional
        :param ignore_fields: Set of field names to ignore during uniqueness validation.
        :type ignore_fields: set[str], optional
        :param exclude_instance: Instance of the model to exclude from the check (useful for updates).
        :type exclude_instance: models.Model, optional
        :param self_scope: Dictionary of additional filters to apply directly to the model query.
        :type self_scope: dict, optional
        :raises ValidationError: If a uniqueness constraint is violated.
        :rtype: None
        """
        model_fields = {f.name for f in model._meta.fields}
        if unique_fields is None:
            unique_fields = {f.name for f in model._meta.fields if f.unique}

        ignore_fields = ignore_fields or set()

        for field in unique_fields:
            if field in ignore_fields or field not in data or field not in model_fields:
                continue

            value = data[field]
            qs = model.objects.filter(**{field: value})

            if self_scope:
                qs = qs.filter(**self_scope)

            if exclude_instance:
                qs = qs.exclude(pk=exclude_instance.pk)

            if qs.exists():
                # noinspection PyBroadException
                try:
                    verbose_name = model._meta.get_field(field).verbose_name
                except Exception:
                    verbose_name = field.replace('_', ' ').capitalize()

                raise ValidationError(
                    f"A record with the same {verbose_name} already exists."
                )