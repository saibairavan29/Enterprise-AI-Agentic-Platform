from django.db import models
from repository.models import KnowledgeRelationship

class RelationshipRepository:
    """
    Data access layer for operations on KnowledgeRelationship.
    """
    def list_by_document(self, knowledge_document_id):
        return KnowledgeRelationship.objects.filter(
            models.Q(source_document_id=knowledge_document_id) | 
            models.Q(target_document_id=knowledge_document_id)
        )

    def create(self, **fields):
        return KnowledgeRelationship.objects.create(**fields)
