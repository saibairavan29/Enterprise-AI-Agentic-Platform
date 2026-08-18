from ingestion.models import Document

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
        """
        Document.objects.filter(id=document_id).update(
            metadata=metadata,
            standardized_record=standardized_record,
            ocr_metadata=ocr_metadata,
            ocr_confidence=ocr_confidence,
            processing_status=status
        )
