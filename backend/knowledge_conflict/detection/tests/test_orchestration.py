from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ingestion.models import Document
from repository.models import KnowledgeDocument, KnowledgeRecord
from ...models import KnowledgeCandidate, KnowledgeConflict
from ...repositories.candidate_repository import CandidateRepository
from ..services.orchestration import ConflictDetectionOrchestrator
from ..repositories.conflict_repository import ConflictRepository

User = get_user_model()

class OrchestrationTests(TestCase):
    """
    E2E integration test suite verifying the ConflictDetectionOrchestrator pipeline runs.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="orch_det_tester", email="orch_det_tester@example.com", password="Password123")
        self.txt_file = SimpleUploadedFile("policy.txt", b"Standard operational document guidelines.")
        
        self.raw_doc = Document.objects.create(
            uploaded_by=self.user,
            file=self.txt_file,
            file_hash="uniquehash999",
            original_name="policy.txt",
            file_size=30,
            mime_type="text/plain",
            parser_type="TEXT"
        )
        
        self.doc1 = KnowledgeDocument.objects.create(
            source_document=self.raw_doc,
            title="Operating Policy Document",
            current_version=1,
            repository_status="ACTIVE",
            raw_content="Operating policy rules details."
        )
        
        self.doc2 = KnowledgeDocument.objects.create(
            title="Operating Policy Document Variant",
            current_version=1,
            repository_status="ACTIVE",
            raw_content="Operating policy rules changed details."
        )

        # Create candidate pair in database (representing same title / similarity window check)
        self.candidate = KnowledgeCandidate.objects.create(
            batch_id="batch_001",
            candidate_hash="candhash001",
            source_document=self.doc1,
            target_document=self.doc2,
            source_segment_id=f"{self.doc1.id}-para-1",
            target_segment_id=f"{self.doc2.id}-para-1",
            source_text="Operating policy rules details.",
            target_text="Operating policy rules changed details.",
            source_page=1,
            target_page=1,
            source_section="Main",
            target_section="Main",
            strategy_used="SameTitleStrategy",
            strategy_confidence=75.0,
            entity_type="DocumentSegment",
            status="GENERATED",
            metadata={}
        )
        
        self.candidate_repo = CandidateRepository()
        self.conflict_repo = ConflictRepository()

    def test_e2e_conflict_detection_orchestrator(self):
        orchestrator = ConflictDetectionOrchestrator()
        report = orchestrator.run_detection()
        
        # Verify execution report fields
        self.assertEqual(report["processed_candidates"], 1)
        self.assertIn("cache_hits", report)
        self.assertIn("cache_misses", report)
        self.assertEqual(report["duplicates"] + report["conflicts"] + report["outdated"] + report["consistent"] + report["unknown"], 1)
        self.assertGreater(report["execution_time"], 0.0)
        
        # Verify KnowledgeConflict is persisted in PostgreSQL
        conflicts_db = KnowledgeConflict.objects.all()
        self.assertEqual(conflicts_db.count(), 1)
        
        conflict = conflicts_db.first()
        self.assertEqual(conflict.knowledge_candidate, self.candidate)
        self.assertEqual(conflict.status, "NEW")
        
        # Assert self-descriptive similarity metrics exist
        self.assertIn("cosine_similarity", conflict.similarity_metrics)
        self.assertIn("overall_similarity", conflict.similarity_metrics)
        
        # Assert processing trace fingerprint exists
        self.assertEqual(conflict.processing_trace["candidate_id"], str(self.candidate.candidate_id))
        self.assertEqual(conflict.processing_trace["similarity_engine"], "CosineSimilarity")
        self.assertIn("execution_time", conflict.processing_trace)
        
        # Verify candidate status transitioned to PROCESSED
        self.candidate.refresh_from_db()
        self.assertEqual(self.candidate.status, "PROCESSED")
