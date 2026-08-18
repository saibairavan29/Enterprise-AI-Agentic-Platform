from repository.exceptions import ValidationException
from ingestion.models import Document

class RepositoryValidator:
    """
    Validator for Repository payloads and updates.
    """
    @staticmethod
    def validate_sync_payload(doc_id, records, metadata):
        if not doc_id:
            raise ValidationException("Document ID is missing.")
            
        if not isinstance(records, list):
            raise ValidationException("Records must be a list of standardized dicts.")

        if not isinstance(metadata, dict):
            raise ValidationException("Metadata must be a dictionary.")

        # Check if ingestion document exists
        if not Document.objects.filter(id=doc_id).exists():
            raise ValidationException(f"Source document with ID {doc_id} does not exist in Phase 1 database.")

    @staticmethod
    def validate_record_update(canonical_data):
        if not isinstance(canonical_data, dict):
            raise ValidationException("Canonical data must be a dictionary.")
        # Any specific enterprise constraints can be added here
        return True
