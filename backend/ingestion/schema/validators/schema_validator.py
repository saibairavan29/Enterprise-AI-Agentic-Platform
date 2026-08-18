from ..exceptions.schema_exceptions import SchemaValidationException
from ..schemas.enterprise_schema import CANONICAL_FIELDS

class SchemaValidator:
    """
    Validator responsible for validating the integrity of the mapped canonical record:
    required values, duplicate target assignments, value conflicts, and invalid field names.
    """
    def validate(self, record_obj, mapping_metadata=None):
        """
        Validates the schema structure. Raises SchemaValidationException if validation rules are violated.
        """
        if not record_obj or not isinstance(record_obj, dict):
            raise SchemaValidationException("Record payload must be a dictionary.")

        # 1. Verify required values
        doc_id = record_obj.get("document_id")
        if not doc_id:
            raise SchemaValidationException("Missing required schema property: document_id")

        entity_type = record_obj.get("entity_type")
        if not entity_type:
            raise SchemaValidationException("Missing required schema property: entity_type")

        # 2. Verify canonical fields match the registry
        canon_fields = record_obj.get("canonical_fields", {})
        if not isinstance(canon_fields, dict):
            raise SchemaValidationException("canonical_fields must be a dictionary.")
            
        for k in canon_fields.keys():
            if k not in CANONICAL_FIELDS:
                raise SchemaValidationException(f"Invalid canonical field name identified: {k}")

        # 3. Evaluate duplicate key conflicts recorded by mappers
        if mapping_metadata:
            conflicts = mapping_metadata.get("conflicts", [])
            if conflicts:
                conflict_desc = ", ".join([f"{c['attempted_key']} vs {c['existing_key']} for {c['canonical_field']}" for c in conflicts])
                raise SchemaValidationException(
                    f"Mapping value conflict detected for canonical targets: {conflict_desc}"
                )

        # 4. Verify empty raw keys do not exist
        additional_fields = record_obj.get("additional_fields", {})
        if not isinstance(additional_fields, dict):
            raise SchemaValidationException("additional_fields must be a dictionary.")

        for k in additional_fields.keys():
            if not str(k).strip():
                raise SchemaValidationException("Empty field names are not allowed within additional_fields.")

        return True
