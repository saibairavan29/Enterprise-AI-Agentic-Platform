from django.core.exceptions import ObjectDoesNotExist
from ..models import ConflictReview, ConflictAuditHistory

class ReviewRepository:
    """
    Data access layer for operations on ConflictReview and ConflictAuditHistory.
    """
    def get_by_id(self, review_id) -> ConflictReview:
        try:
            return ConflictReview.objects.get(review_id=review_id)
        except ObjectDoesNotExist:
            return None

    def get_by_conflict_id(self, conflict_id) -> ConflictReview:
        try:
            return ConflictReview.objects.filter(conflict__conflict_id=conflict_id).first()
        except ObjectDoesNotExist:
            return None

    def get_pending_reviews(self) -> list:
        return list(ConflictReview.objects.filter(review_status__in=['PENDING', 'UNDER_REVIEW']))

    def get_reviewer_actions(self, reviewer) -> list:
        return list(ConflictReview.objects.filter(reviewer=reviewer))

    def get_history(self) -> list:
        return list(ConflictAuditHistory.objects.all().order_by('-timestamp'))

    def create_review(self, **fields) -> ConflictReview:
        return ConflictReview.objects.create(**fields)

    def save_review(self, review_obj) -> ConflictReview:
        review_obj.save()
        return review_obj
