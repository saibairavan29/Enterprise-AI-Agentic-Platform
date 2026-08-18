from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from repository.models import KnowledgeDocument
from ...models import KnowledgeCandidate, KnowledgeConflict
from ..models import ConflictReview

User = get_user_model()

class APITests(APITestCase):
    """
    Test suite validating REST endpoints, route permissions validation,
    and review/resolution POST API pipelines.
    """
    def setUp(self):
        self.reader = User.objects.create_user(username="reader_user", email="reader_user@example.com", password="Password123", role="reader")
        self.analyst = User.objects.create_user(username="analyst_user", email="analyst_user@example.com", password="Password123", role="analyst")
        self.admin = User.objects.create_user(username="admin_user", email="admin_user@example.com", password="Password123", role="admin")
        
        self.doc1 = KnowledgeDocument.objects.create(title="Doc A", current_version=1)
        self.doc2 = KnowledgeDocument.objects.create(title="Doc B", current_version=1)
        
        self.cand = KnowledgeCandidate.objects.create(
            batch_id="batch_api",
            candidate_hash="hash_api",
            source_document=self.doc1,
            target_document=self.doc2,
            source_segment_id="s1",
            target_segment_id="t1",
            source_text="A",
            target_text="B",
            strategy_used="SameTitleStrategy",
            strategy_confidence=80.0
        )
        
        self.conflict = KnowledgeConflict.objects.create(
            knowledge_candidate=self.cand,
            source_document=self.doc1,
            target_document=self.doc2,
            conflict_type="CONFLICTING",
            overall_similarity=0.80,
            similarity_metrics={},
            confidence_score=0.85,
            embedding_model="MiniLM",
            classifier_used="ConflictClassifier",
            status="NEW"
        )

    def test_reader_permissions_insufficient(self):
        self.client.force_authenticate(user=self.reader)
        
        # Reader should be able to view conflicts lists
        response = self.client.get('/api/v1/conflicts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        # Reader should NOT be able to run detection
        response_post = self.client.post('/api/v1/conflicts/')
        self.assertEqual(response_post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response_post.data["success"])
        
        # Reader should NOT be able to post reviews
        response_review = self.client.post(f'/api/v1/conflicts/{self.conflict.conflict_id}/review/', {"action": "start"})
        self.assertEqual(response_review.status_code, status.HTTP_400_BAD_REQUEST)

    def test_analyst_review_workflow_api(self):
        self.client.force_authenticate(user=self.analyst)
        
        # Start review API
        response = self.client.post(f'/api/v1/conflicts/{self.conflict.conflict_id}/review/', {"action": "start"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        review_id = response.data["data"]["review_id"]
        review_pk = response.data["data"]["id"]
        
        # Submit decision API
        response_dec = self.client.post(f'/api/v1/conflicts/{self.conflict.conflict_id}/review/', {
            "action": "submit",
            "review_id": review_id,
            "decision": "CONFIRMED",
            "status": "APPROVED",
            "comments": "Matches identified discrepancy."
        })
        self.assertEqual(response_dec.status_code, status.HTTP_200_OK)
        
        # Execute Resolution API
        response_res = self.client.post(f'/api/v1/conflicts/{self.conflict.conflict_id}/resolve/', {
            "review_id": review_id,
            "resolution": "IGNORE"
        })
        self.assertEqual(response_res.status_code, status.HTTP_200_OK)
        self.assertEqual(response_res.data["data"]["status"], "SUCCESS")
        
        # Verify conflict model transitioned status to VERIFIED
        self.conflict.refresh_from_db()
        self.assertEqual(self.conflict.status, "VERIFIED")
