from django.core.exceptions import ObjectDoesNotExist
from ..models import KnowledgeCandidate

class CandidateRepository:
    """
    Data access layer for operations on KnowledgeCandidate database records,
    decoupling service actions from direct Django ORM calls.
    """
    def get_by_id(self, candidate_id) -> KnowledgeCandidate:
        try:
            return KnowledgeCandidate.objects.get(candidate_id=candidate_id)
        except ObjectDoesNotExist:
            return None

    def get_by_hash(self, candidate_hash) -> KnowledgeCandidate:
        try:
            return KnowledgeCandidate.objects.get(candidate_hash=candidate_hash)
        except ObjectDoesNotExist:
            return None

    def list_by_batch(self, batch_id) -> list:
        return list(KnowledgeCandidate.objects.filter(batch_id=batch_id))

    def list_by_document(self, document_id) -> list:
        return list(KnowledgeCandidate.objects.filter(
            models.Q(source_document_id=document_id) | models.Q(target_document_id=document_id)
        ))

    def create(self, **fields) -> KnowledgeCandidate:
        return KnowledgeCandidate.objects.create(**fields)

    def bulk_create(self, candidates_list) -> list:
        """
        Bulk inserts KnowledgeCandidate objects, filtering out duplicates by hash.
        Returns the list of created records.
        """
        if not candidates_list:
            return []
            
        # Exclude candidates that already exist with the same hash
        existing_hashes = set(KnowledgeCandidate.objects.filter(
            candidate_hash__in=[c.candidate_hash for c in candidates_list]
        ).values_list('candidate_hash', flat=True))
        
        filtered_list = [c for c in candidates_list if c.candidate_hash not in existing_hashes]
        if not filtered_list:
            return []
            
        return KnowledgeCandidate.objects.bulk_create(filtered_list)

    def delete_by_batch(self, batch_id):
        return KnowledgeCandidate.objects.filter(batch_id=batch_id).delete()

    def archive_by_batch(self, batch_id):
        """
        Updates the status of all candidates in a batch to ARCHIVED.
        """
        return KnowledgeCandidate.objects.filter(batch_id=batch_id).update(status='ARCHIVED')

    def get_all(self) -> list:
        return list(KnowledgeCandidate.objects.all())
