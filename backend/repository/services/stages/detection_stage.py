from repository.repositories.document_repository import DocumentRepository
from ingestion.models import Document

class DetectionStage:
    """
    Stage 2: Detect whether a matching document exists in the repository 
    by checking file hash and Title match strategies.
    """
    def __init__(self):
        self.doc_repo = DocumentRepository()

    def execute(self, context):
        doc_id = context.get('document_id')
        source_doc = Document.objects.get(id=doc_id)
        
        context['source_doc'] = source_doc
        context['title'] = source_doc.original_name
        context['checksum'] = source_doc.file_hash
        context['repository_size'] = source_doc.file_size
        
        # Check by content hash lookup
        existing_doc = self.doc_repo.get_by_hash(source_doc.file_hash)
        if not existing_doc:
            # Fallback to matching standard metadata titles
            existing_doc = self.doc_repo.get_by_title(source_doc.original_name)

        context['existing_doc'] = existing_doc
        return context
