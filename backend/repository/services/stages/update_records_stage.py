from repository.repositories.record_repository import RecordRepository
from repository.models import KnowledgeRecord

class UpdateRecordsStage:
    """
    Stage 6: Remove old canonical records and bulk-insert the newly synchronized 
    records list inside the target KnowledgeDocument context.
    """
    def __init__(self):
        self.record_repo = RecordRepository()

    def execute(self, context):
        knowledge_doc = context.get('knowledge_document')
        records = context.get('records', [])
        
        # If it's an update, purge old entries to avoid duplicate constraints
        if context.get('existing_doc'):
            self.record_repo.delete_by_document(knowledge_doc.id)
            
        # Compile record objects
        record_instances = []
        for r in records:
            if not isinstance(r, dict):
                continue
                
            # If the record is wrapped in the standard Core mapping envelope:
            if 'canonical_fields' in r:
                canonical_data = r['canonical_fields'] or {}
                additional_fields = r.get('additional_fields') or {}
                entity_type = r.get('entity_type', 'generic')
            else:
                # Direct canonical list updates:
                canonical_data = r
                additional_fields = {}
                entity_type = context.get('entity_type', 'generic')
                
            record_instances.append(
                KnowledgeRecord(
                    knowledge_document=knowledge_doc,
                    entity_type=entity_type,
                    canonical_data=canonical_data,
                    additional_fields=additional_fields,
                    embedding_status='NOT_GENERATED',
                    embedding_reference=None
                )
            )

        # Bulk create records
        if record_instances:
            self.record_repo.bulk_create(record_instances)

        return context
