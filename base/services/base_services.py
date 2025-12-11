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
                raise ValidationError(f'Missing required fields: {', '.join(missing)}')

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
                    resolved[attr] = model.objects.get(id=value, is_active=True)
                except ObjectDoesNotExist:
                    raise ValidationError(f'{attr} with id={value} does not exist or is inactive.')
            else:
                resolved[field] = value

        return resolved
