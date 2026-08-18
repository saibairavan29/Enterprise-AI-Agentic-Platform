from django.test import TestCase
from django.contrib.auth import get_user_model
from repository.models import KnowledgeDocument
from ...models import KnowledgeCandidate, KnowledgeConflict
from ..models import ConflictReview, ConflictAuditHistory
from ..repositories.review_repository import ReviewRepository
from ..audit.audit_logger import ConflictAuditLogger

User = get_user_model()

class ReviewTests(TestCase):
    """
    Test suite validating human reviews db creation, audit history tracking,
    and repositories query wrapper actions.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="reviewer_tester", email="reviewer_tester@example.com", password="Password123", role="analyst")
        self.doc1 = KnowledgeDocument.objects.create(title="Doc A", current_version=1)
        self.doc2 = KnowledgeDocument.objects.create(title="Doc B", current_version=1)
        
        self.cand = KnowledgeCandidate.objects.create(
            batch_id="batch_01",
            candidate_hash="hash01",
            source_document=self.doc1,
            target_document=self.doc2,
            source_segment_id="s1",
            target_segment_id="t1",
            source_text="Text A",
            target_text="Text B",
            strategy_used="SameTitleStrategy",
            strategy_confidence=80.0
        )
        
        self.conflict = KnowledgeConflict.objects.create(
            knowledge_candidate=self.cand,
            source_document=self.doc1,
            target_document=self.doc2,
            conflict_type="CONFLICTING",
            severity="MEDIUM",
            overall_similarity=0.85,
            similarity_metrics={},
            confidence_score=0.90,
            embedding_model="MiniLM",
            classifier_used="ConflictClassifier",
            status="NEW"
        )
        self.review_repo = ReviewRepository()

    def test_review_creation_and_repo_fetches(self):
        # Create review
        review = self.review_repo.create_review(
            conflict=self.conflict,
            reviewer=self.user,
            review_status="PENDING"
        )
        self.assertIsNotNone(review.review_id)
        self.assertEqual(review.review_status, "PENDING")
        
        # Test repository fetches
        pending = self.review_repo.get_pending_reviews()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0], review)
        
        actions = self.review_repo.get_reviewer_actions(self.user)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0], review)

    def test_audit_history_logs_immutable(self):
        ConflictAuditLogger.log_action(
            conflict=self.conflict,
            user=self.user,
            action="Started validation.",
            action_type="REVIEW_STARTED",
            old_status="NEW",
            new_status="UNDER_REVIEW",
            comments="Assigned to reviewer."
        )
        
        audits = ConflictAuditHistory.objects.all()
        self.assertEqual(audits.count(), 1)
        
        log = audits.first()
        self.assertEqual(log.action_type, "REVIEW_STARTED")
        self.assertEqual(log.old_status, "NEW")
        self.assertEqual(log.new_status, "UNDER_REVIEW")
        self.assertEqual(log.user, self.user)
