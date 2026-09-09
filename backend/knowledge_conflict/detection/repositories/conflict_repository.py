from django.core.exceptions import ObjectDoesNotExist
from ...models import KnowledgeConflict

class ConflictRepository:
    """
    Data access layer for operations on KnowledgeConflict database records.
    Decouples server logic from raw ORM query definitions.
    """
    def get_by_id(self, conflict_id) -> KnowledgeConflict:
        try:
            return KnowledgeConflict.objects.get(conflict_id=conflict_id)
        except ObjectDoesNotExist:
            return None

    def list_by_status(self, status: str) -> list:
        return list(KnowledgeConflict.objects.filter(status=status))

    def get_pending(self) -> list:
        """Returns all conflicts awaiting analyst review."""
        return list(KnowledgeConflict.objects.filter(status__in=['NEW', 'REVIEW_PENDING']))

    def create(self, **fields) -> KnowledgeConflict:
        return KnowledgeConflict.objects.create(**fields)

    def bulk_create(self, conflicts_list, batch_size=500) -> list:
        if not conflicts_list:
            return []
        return KnowledgeConflict.objects.bulk_create(conflicts_list, batch_size=batch_size)

    def bulk_update(self, conflicts_list, fields_to_update, batch_size=500) -> int:
        if not conflicts_list:
            return 0
        return KnowledgeConflict.objects.bulk_update(conflicts_list, fields_to_update, batch_size=batch_size)

    def archive(self, conflict_id) -> bool:
        """Soft-deletes/archives a conflict entry."""
        rows = KnowledgeConflict.objects.filter(id=conflict_id).update(status='ARCHIVED')
        return rows > 0

    def mark_verified(self, conflict_id) -> bool:
        """Sets the status of a conflict to VERIFIED."""
        rows = KnowledgeConflict.objects.filter(id=conflict_id).update(status='VERIFIED')
        return rows > 0
