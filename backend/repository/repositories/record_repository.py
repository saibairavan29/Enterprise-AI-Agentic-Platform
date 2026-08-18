from django.core.exceptions import ObjectDoesNotExist
from repository.models import KnowledgeRecord

class RecordRepository:
    """
    Data access layer for operations on KnowledgeRecord, incorporating 
    generic PostgreSQL JSONField querying options.
    """
    def get_by_id(self, record_id):
        try:
            return KnowledgeRecord.objects.get(id=record_id)
        except ObjectDoesNotExist:
            return None

    def list_by_document(self, knowledge_document_id):
        return KnowledgeRecord.objects.filter(knowledge_document_id=knowledge_document_id)

    def create(self, **fields):
        return KnowledgeRecord.objects.create(**fields)

    def bulk_create(self, records_list):
        return KnowledgeRecord.objects.bulk_create(records_list)

    def delete_by_document(self, knowledge_document_id):
        return KnowledgeRecord.objects.filter(knowledge_document_id=knowledge_document_id).delete()

    def filter_records(self, field, value=None, contains=None):
        """
        Dynamically construct lookups into django JSONField to query 
        canonical data attributes (such as department, email, etc.)
        """
        queryset = KnowledgeRecord.objects.all()
        if not field:
            return queryset

        if value is not None:
            # Matches field value exactly (case-insensitive)
            lookup = f"canonical_data__{field}__iexact"
            return queryset.filter(**{lookup: value})
        elif contains is not None:
            # Matches field containing substring (case-insensitive)
            lookup = f"canonical_data__{field}__icontains"
            return queryset.filter(**{lookup: contains})

        return queryset
