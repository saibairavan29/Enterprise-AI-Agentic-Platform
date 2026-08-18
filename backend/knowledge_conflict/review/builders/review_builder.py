import uuid
from ..models import ConflictReview

class ReviewBuilder:
    """
    Builder class to instantiate ConflictReview models.
    """
    @staticmethod
    def build(conflict, reviewer, review_status: str = 'PENDING') -> ConflictReview:
        return ConflictReview(
            review_id=uuid.uuid4(),
            conflict=conflict,
            reviewer=reviewer,
            review_status=review_status,
            comments=""
        )
