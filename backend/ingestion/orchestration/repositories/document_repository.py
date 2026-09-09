from ingestion.models import Document

from common.json_utils import enforce_json_boundary

class DocumentRepository:
    """
    Repository responsible for CRUD queries on the Document Django database model.
    """
    def get_by_id(self, document_id) -> Document:
        """Fetches Document by primary key ID."""
        try:
            return Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return None

    def update_document_status(self, document_id, status):
        """Updates the processing status of a document."""
        Document.objects.filter(id=document_id).update(processing_status=status)

    def save_standardized_data(self, document_id, metadata, standardized_record, ocr_metadata, ocr_confidence, status):
        """
        Saves all finalized ingestion outputs to the Document database record in one call.
        Enforces a hard JSON-serialization boundary before ORM update.
        """
        Document.objects.filter(id=document_id).update(
            metadata=enforce_json_boundary(metadata, label="Document.metadata"),
            standardized_record=enforce_json_boundary(standardized_record, label="Document.standardized_record"),
            ocr_metadata=enforce_json_boundary(ocr_metadata, label="Document.ocr_metadata"),
            ocr_confidence=ocr_confidence,
            processing_status=status
        )

