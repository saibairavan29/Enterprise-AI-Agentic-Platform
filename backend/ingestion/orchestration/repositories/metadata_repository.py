from ingestion.models import Document

class MetadataRepository:
    """
    Repository responsible for updates to metadata properties on Document.
    """
    def update_metadata(self, document_id, metadata):
        """Updates the metadata JSON field on Document."""
        Document.objects.filter(id=document_id).update(metadata=metadata)
