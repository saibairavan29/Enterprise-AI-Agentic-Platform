from repository.repositories.audit_repository import AuditRepository

class AuditStage:
    """
    Stage 7: Create a formal RepositoryAuditEntry marking the synchronization, 
    associating user audit info, reason, and pipeline tracking ID.
    """
    def __init__(self):
        self.audit_repo = AuditRepository()

    def execute(self, context):
        doc = context.get('knowledge_document')
        user_obj = context.get('user')
        username = user_obj.username if user_obj else 'SYSTEM'
        
        reason = context.get('reason')
        if not reason:
            if context.get('existing_doc'):
                reason = f"Document updated to version {doc.current_version}."
            else:
                reason = "Initial document synchronization."

        self.audit_repo.create(
            knowledge_document=doc,
            action='SYNC',
            user=username,
            reason=reason,
            pipeline_id=context.get('pipeline_id', '')
        )
        return context
