from django.test import TestCase
from django.contrib.auth import get_user_model
from repository.models import KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeRecord
from ...models import KnowledgeCandidate, KnowledgeConflict
from ..services.review_service import ReviewService

User = get_user_model()

class ResolutionTests(TestCase):
    """
    Test suite validating conflict resolution execution routines, repository
    updates, version history records generation, and back-reference review linkages.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="res_tester", email="res_tester@example.com", password="Password123", role="admin")
        self.doc1 = KnowledgeDocument.objects.create(
            title="SOP V1", 
            current_version=1,
            raw_content="Source procedures details."
        )
        self.doc2 = KnowledgeDocument.objects.create(
            title="SOP V1 Variant", 
            current_version=1,
            raw_content="Target procedures mismatch details."
        )
        
        self.rec1 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc1,
            entity_type="Staff",
            canonical_data={"employee_id": "EMP100", "salary": 4000}
        )

        self.cand = KnowledgeCandidate.objects.create(
            batch_id="batch_res",
            candidate_hash="hash_res",
            source_document=self.doc1,
            target_document=self.doc2,
            source_segment_id="s1",
            target_segment_id="t1",
            source_text="Source procedures details.",
            target_text="Target procedures mismatch details.",
            strategy_used="SameTitleStrategy",
            strategy_confidence=80.0
        )
        
        self.conflict = KnowledgeConflict.objects.create(
            knowledge_candidate=self.cand,
            source_document=self.doc1,
            target_document=self.doc2,
            conflict_type="CONFLICTING",
            severity="HIGH",
            overall_similarity=0.80,
            similarity_metrics={},
            confidence_score=0.85,
            embedding_model="MiniLM",
            classifier_used="ConflictClassifier",
            status="NEW"
        )
        
        self.review_service = ReviewService()

    def test_resolution_keep_source(self):
        # Start review and approve it first
        review = self.review_service.start_review(self.conflict.conflict_id, self.user)
        self.review_service.submit_decision(
            review_id=review.review_id,
            decision="CONFIRMED",
            status="APPROVED",
            comments="Approved for keep source resolution.",
            user=self.user
        )
        
        # Execute Resolution
        result = self.review_service.execute_resolution(
            review_id=review.review_id,
            resolution_type="KEEP_SOURCE",
            user=self.user
        )
        
        # Verify resolution DTO result
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.old_version, 1)
        self.assertEqual(result.new_version, 2)
        self.assertEqual(result.document_id, self.doc2.id)
        
        # Verify KnowledgeDocumentVersion carries linking JSON
        versions = KnowledgeDocumentVersion.objects.filter(knowledge_document=self.doc2)
        self.assertEqual(versions.count(), 1)
        
        ver_snapshot = versions.first()
        self.assertEqual(ver_snapshot.version, 2)
        self.assertEqual(ver_snapshot.checksum, f"link-{review.review_id}")
        self.assertEqual(ver_snapshot.change_summary["resolution"], "KEEP_SOURCE")
        self.assertEqual(ver_snapshot.change_summary["review_id"], str(review.review_id))

    def test_resolution_manual_edit_updates_records(self):
        review = self.review_service.start_review(self.conflict.conflict_id, self.user)
        
        # Execute MANUAL_EDIT resolution with field adjustments
        custom_fields = {"salary": 4500}
        result = self.review_service.execute_resolution(
            review_id=review.review_id,
            resolution_type="MANUAL_EDIT",
            user=self.user,
            custom_edit_data=custom_fields
        )
        
        self.assertEqual(result.status, "SUCCESS")
        
        # Verify document record updated canonical salary field
        self.rec1.refresh_from_db()
        self.assertEqual(self.rec1.canonical_data["salary"], 4500)
