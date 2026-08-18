from repository.repositories.version_repository import VersionRepository

class VersionHistoryStage:
    """
    Stage 3: If the document exists, archive its current state to version history 
    before the document is updated with new ingestion details.
    """
    def __init__(self):
        self.version_repo = VersionRepository()

    def execute(self, context):
        existing_doc = context.get('existing_doc')
        if existing_doc:
            # Create a snapshot version representing current state
            version_snapshot = self.version_repo.create(
                knowledge_document=existing_doc,
                version=existing_doc.current_version,
                raw_content=existing_doc.raw_content,
                metadata=existing_doc.metadata,
                checksum=existing_doc.source_document.file_hash if existing_doc.source_document else '',
                change_summary={},  # Will be populated in VersionDiffStage
                source_document_id=existing_doc.source_document.id if existing_doc.source_document else None,
                reason_for_update=context.get('reason', 'Automatic Document Ingestion Update'),
                updated_by=context.get('user')
            )
            context['version_snapshot'] = version_snapshot
            context['version'] = existing_doc.current_version + 1
        else:
            context['version'] = 1
            context['version_snapshot'] = None

        return context
