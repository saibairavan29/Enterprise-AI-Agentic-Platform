from django.core.exceptions import ObjectDoesNotExist
from repository.models import KnowledgeDocumentVersion

class VersionRepository:
    """
    Data access layer for operations on KnowledgeDocumentVersion.
    """
    def list_by_document(self, knowledge_document_id):
        return KnowledgeDocumentVersion.objects.filter(knowledge_document_id=knowledge_document_id)

    def get_latest_version(self, knowledge_document_id):
        return KnowledgeDocumentVersion.objects.filter(
            knowledge_document_id=knowledge_document_id
        ).order_by('-version').first()

    def create(self, **fields):
        return KnowledgeDocumentVersion.objects.create(**fields)
