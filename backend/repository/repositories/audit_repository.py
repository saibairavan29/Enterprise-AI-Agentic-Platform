from repository.models import RepositoryAuditEntry

class AuditRepository:
    """
    Data access layer for operations on RepositoryAuditEntry.
    """
    def list_all(self):
        return RepositoryAuditEntry.objects.all()

    def list_by_document(self, knowledge_document_id):
        return RepositoryAuditEntry.objects.filter(knowledge_document_id=knowledge_document_id)

    def create(self, **fields):
        return RepositoryAuditEntry.objects.create(**fields)
