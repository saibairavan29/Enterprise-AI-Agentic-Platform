from django.core.exceptions import ObjectDoesNotExist
from repository.models import KnowledgeDocument

from django.db.models import Q

class DocumentRepository:
    """
    Data access layer for operations on KnowledgeDocument.
    """
    def get_by_id(self, document_id):
        try:
            return KnowledgeDocument.objects.get(id=document_id)
        except ObjectDoesNotExist:
            return None

    def get_by_source_document_id(self, source_doc_id):
        try:
            return KnowledgeDocument.objects.get(source_document_id=source_doc_id)
        except ObjectDoesNotExist:
            return None

    def get_by_title(self, title):
        # We can also search by metadata hash if needed inside services,
        # but title or filename is fine for direct checks.
        return KnowledgeDocument.objects.filter(title=title, repository_status='ACTIVE').first()

    def get_by_hash(self, file_hash):
        return KnowledgeDocument.objects.filter(source_document__file_hash=file_hash).first()

    def list_all(self):
        return KnowledgeDocument.objects.all()

    def list_active(self):
        return KnowledgeDocument.objects.filter(
            repository_status='ACTIVE'
        ).filter(
            Q(folder__isnull=True) | Q(folder__is_deleted=False)
        ).exclude(
            source_document__status__in=['deleted', 'DELETED', 'archived', 'FAILED']
        )

    def create(self, **fields):
        return KnowledgeDocument.objects.create(**fields)

    def save(self, document_obj):
        document_obj.save()
        return document_obj

    def soft_delete(self, document_obj):
        document_obj.repository_status = 'DELETED'
        document_obj.save()
        # Preserve KnowledgeRecord instances for Employee Directory stability
        return document_obj
