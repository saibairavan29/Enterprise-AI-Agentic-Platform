from django.utils import timezone
from repository.repositories.document_repository import DocumentRepository

class UpdateDocumentStage:
    """
    Stage 5: Create or update the KnowledgeDocument database entry 
    with current version, metadata, text content, and aggregate statistics.
    """
    def __init__(self):
        self.doc_repo = DocumentRepository()

    def execute(self, context):
        existing_doc = context.get('existing_doc')
        source_doc = context.get('source_doc')
        title = context.get('title')
        version = context.get('version', 1)
        metadata = context.get('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}
        if source_doc and source_doc.metadata and isinstance(source_doc.metadata, dict):
            if "repository_type" in source_doc.metadata and "repository_type" not in metadata:
                metadata["repository_type"] = source_doc.metadata["repository_type"]
        
        # Get raw content from parser result or source metadata
        raw_content = ""
        if context.get('raw_content'):
            raw_content = context['raw_content']
        elif hasattr(context, 'parser_result') and context.parser_result:
            raw_content = context.parser_result.get('content', '')
            
        record_count = len(context.get('records', []))
        repository_size = context.get('repository_size', 0)

        if existing_doc:
            existing_doc.title = title
            existing_doc.current_version = version
            existing_doc.repository_status = 'ACTIVE'
            existing_doc.metadata = metadata
            existing_doc.raw_content = raw_content
            existing_doc.record_count = record_count
            existing_doc.version_count = version
            existing_doc.last_sync = timezone.now()
            existing_doc.repository_size = repository_size
            
            # Save using repository
            self.doc_repo.save(existing_doc)
            context['knowledge_document'] = existing_doc
        else:
            # Create a brand new active KnowledgeDocument
            new_doc = self.doc_repo.create(
                source_document=source_doc,
                title=title,
                current_version=version,
                repository_status='ACTIVE',
                metadata=metadata,
                raw_content=raw_content,
                record_count=record_count,
                version_count=version,
                last_sync=timezone.now(),
                repository_size=repository_size
            )
            context['knowledge_document'] = new_doc

        return context
