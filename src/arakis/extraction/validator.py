"""Field validation for extraction data.

Validates extracted data against schema constraints and rules.
"""

from typing import Any

from arakis.models.extraction import ExtractionField, ExtractionSchema, FieldType


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class FieldValidator:
    """Validates extracted field values against schema constraints."""

    def validate_field(
        self, field: ExtractionField, value: Any, raise_on_error: bool = False
    ) -> tuple[bool, list[str]]:
        """
        Validate a single field value against its schema definition.

        Args:
            field: Field definition from schema
            value: Extracted value to validate
            raise_on_error: If True, raise ValidationError instead of returning errors

        Returns:
            Tuple of (is_valid, list_of_errors)

        Raises:
            ValidationError: If raise_on_error=True and validation fails
        """
        errors = []

        # Check if None/missing
        if value is None:
            if field.required:
                errors.append(f"Field '{field.name}' is required but missing")
            return len(errors) == 0, errors

        # Type-specific validation
        if field.field_type == FieldType.NUMERIC:
            errors.extend(self._validate_numeric(field, value))
        elif field.field_type == FieldType.CATEGORICAL:
            errors.extend(self._validate_categorical(field, value))
        elif field.field_type == FieldType.TEXT:
            errors.extend(self._validate_text(field, value))
        elif field.field_type == FieldType.DATE:
            errors.extend(self._validate_date(field, value))
        elif field.field_type == FieldType.BOOLEAN:
            errors.extend(self._validate_boolean(field, value))
        elif field.field_type == FieldType.LIST:
            errors.extend(self._validate_list(field, value))

        is_valid = len(errors) == 0

        if not is_valid and raise_on_error:
            raise ValidationError(
                f"Validation failed for field '{field.name}': {'; '.join(errors)}"
            )

        return is_valid, errors

    def _validate_numeric(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate numeric field."""
        errors = []

        # Try to convert to number
        try:
            if isinstance(value, str):
                # Try to parse string like "50", "50.5", "50-60" (range)
                if "-" in value and not value.startswith("-"):
                    # Handle range like "50-60"
                    parts = value.split("-")
                    if len(parts) == 2:
                        num_value = (float(parts[0]) + float(parts[1])) / 2
                    else:
                        errors.append(f"Cannot parse numeric value: {value}")
                        return errors
                else:
                    num_value = float(value)
            else:
                num_value = float(value)
        except (ValueError, TypeError):
            errors.append(f"Value '{value}' is not numeric")
            return errors

        # Check constraints
        rules = field.validation_rules

        if "min" in rules and num_value < rules["min"]:
            errors.append(f"Value {num_value} is below minimum {rules['min']}")

        if "max" in rules and num_value > rules["max"]:
            errors.append(f"Value {num_value} is above maximum {rules['max']}")

        return errors

    def _validate_categorical(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate categorical field."""
        errors = []

        value_str = str(value).lower()

        if "allowed_values" in field.validation_rules:
            allowed = [str(v).lower() for v in field.validation_rules["allowed_values"]]
            if value_str not in allowed:
                errors.append(
                    f"Value '{value}' is not in allowed values: {field.validation_rules['allowed_values']}"
                )

        return errors

    def _validate_text(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate text field."""
        errors = []

        if not isinstance(value, str):
            value = str(value)

        rules = field.validation_rules

        if "max_length" in rules and len(value) > rules["max_length"]:
            errors.append(f"Text length {len(value)} exceeds maximum {rules['max_length']}")

        if "min_length" in rules and len(value) < rules["min_length"]:
            errors.append(f"Text length {len(value)} is below minimum {rules['min_length']}")

        return errors

    def _validate_date(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate date field."""
        errors = []

        # Accept various date formats
        value_str = str(value)

        # Basic format checks
        if not any(char.isdigit() for char in value_str):
            errors.append(f"Date value '{value}' does not contain any digits")

        return errors

    def _validate_boolean(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate boolean field."""
        errors = []

        if not isinstance(value, bool):
            # Try to convert string representations
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower not in ["true", "false", "yes", "no", "1", "0"]:
                    errors.append(f"Value '{value}' is not a valid boolean")
            else:
                errors.append(f"Value '{value}' is not boolean")

        return errors

    def _validate_list(self, field: ExtractionField, value: Any) -> list[str]:
        """Validate list field."""
        errors = []

        if not isinstance(value, list):
            errors.append(f"Value is not a list: {type(value)}")
            return errors

        rules = field.validation_rules

        if "min_items" in rules and len(value) < rules["min_items"]:
            errors.append(f"List has {len(value)} items, minimum is {rules['min_items']}")

        if "max_items" in rules and len(value) > rules["max_items"]:
            errors.append(f"List has {len(value)} items, maximum is {rules['max_items']}")

        if "allowed_values" in rules:
            allowed = [str(v).lower() for v in rules["allowed_values"]]
            for item in value:
                if str(item).lower() not in allowed:
                    errors.append(
                        f"List item '{item}' is not in allowed values: {rules['allowed_values']}"
                    )

        return errors

    def validate_extraction(
        self, schema: ExtractionSchema, data: dict[str, Any], raise_on_error: bool = False
    ) -> tuple[bool, dict[str, list[str]]]:
        """
        Validate all fields in an extraction against schema.

        Args:
            schema: Extraction schema
            data: Extracted data dictionary
            raise_on_error: If True, raise ValidationError on first error

        Returns:
            Tuple of (all_valid, field_errors_dict)

        Raises:
            ValidationError: If raise_on_error=True and any validation fails
        """
        field_errors: dict[str, list[str]] = {}
        all_valid = True

        # Validate each field
        for field in schema.fields:
            value = data.get(field.name)
            is_valid, errors = self.validate_field(field, value, raise_on_error=False)

            if not is_valid:
                field_errors[field.name] = errors
                all_valid = False

                if raise_on_error:
                    raise ValidationError(
                        f"Validation failed for field '{field.name}': {'; '.join(errors)}"
                    )

        # Check for unexpected fields
        schema_field_names = {f.name for f in schema.fields}
        unexpected_fields = set(data.keys()) - schema_field_names
        if unexpected_fields:
            field_errors["_unexpected"] = [
                f"Unexpected fields not in schema: {', '.join(unexpected_fields)}"
            ]
            all_valid = False

        return all_valid, field_errors


# Singleton validator instance
_validator = FieldValidator()


def validate_field(
    field: ExtractionField, value: Any, raise_on_error: bool = False
) -> tuple[bool, list[str]]:
    """
    Validate a single field value.

    Convenience function for the singleton validator.

    Args:
        field: Field definition
        value: Value to validate
        raise_on_error: If True, raise ValidationError on failure

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    return _validator.validate_field(field, value, raise_on_error)


def validate_extraction(
    schema: ExtractionSchema, data: dict[str, Any], raise_on_error: bool = False
) -> tuple[bool, dict[str, list[str]]]:
    """
    Validate extracted data against schema.

    Convenience function for the singleton validator.

    Args:
        schema: Extraction schema
        data: Extracted data
        raise_on_error: If True, raise ValidationError on failure

    Returns:
        Tuple of (all_valid, field_errors_dict)
    """
    return _validator.validate_extraction(schema, data, raise_on_error)
