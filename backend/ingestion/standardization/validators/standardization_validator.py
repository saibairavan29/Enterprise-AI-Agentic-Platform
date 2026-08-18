import re
from ..exceptions.standardization_exceptions import StandardizationValidationException

class StandardizationValidator:
    """
    Validator responsible for validating type constraints, email patterns,
    date patterns, and number ranges inside the standardized canonical record.
    """
    def validate(self, record):
        """
        Validates the standardized canonical record dictionary.
        Raises StandardizationValidationException on failures.
        """
        if not record or not isinstance(record, dict):
            raise StandardizationValidationException("Standardized record must be a dictionary.")

        # 1. Check required headers
        if not record.get("document_id"):
            raise StandardizationValidationException("Missing required schema property: document_id")
        if not record.get("entity_type"):
            raise StandardizationValidationException("Missing required schema property: entity_type")

        # 2. Check canonical structure
        canon_fields = record.get("canonical_fields", {})
        if not isinstance(canon_fields, dict):
            raise StandardizationValidationException("canonical_fields must be a dictionary.")

        # Validate joining_date format
        joining_date = canon_fields.get("joining_date")
        if joining_date is not None:
            if not isinstance(joining_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", joining_date):
                raise StandardizationValidationException(f"Standardization date constraint violation: joining_date must be YYYY-MM-DD format, got: {joining_date}")

        # Validate salary bounds
        salary = canon_fields.get("salary")
        if salary is not None:
            if not isinstance(salary, (int, float)) or salary < 0:
                raise StandardizationValidationException(f"Standardization numeric constraint violation: salary must be non-negative, got: {salary}")

        # Validate email pattern structure
        email = canon_fields.get("email")
        if email is not None:
            if not isinstance(email, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise StandardizationValidationException(f"Standardization text constraint violation: email formatting invalid, got: {email}")

        return True
PostgresStandardizationValidator = StandardizationValidator
