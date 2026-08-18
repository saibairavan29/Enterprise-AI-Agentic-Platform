from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ingestion.models import Document
from repository.models import KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeRecord
from ..models import KnowledgeCandidate
from ..services.orchestration import CandidateOrchestrationService
from ..utils.deduplicator import CandidateDeduplicator

User = get_user_model()

class OrchestrationTests(TestCase):
    """
    Integration test suite validating CandidateOrchestrationService workflows, E2E processing
    statistics report shapes, deduplications, and database persistence results.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="orch_tester", email="orch_tester@example.com", password="Password123")
        self.txt_file = SimpleUploadedFile("procedure.txt", b"Document operational guidelines.")
        
        self.raw_doc = Document.objects.create(
            uploaded_by=self.user,
            file=self.txt_file,
            file_hash="uniquehash001",
            original_name="procedure.txt",
            file_size=20,
            mime_type="text/plain",
            parser_type="TEXT"
        )
        
        # Setup 2 documents with same title to trigger SameTitleStrategy
        self.doc1 = KnowledgeDocument.objects.create(
            source_document=self.raw_doc,
            title="Operating Procedures Document",
            current_version=2,
            repository_status="ACTIVE",
            raw_content="Version 2 body operational procedures text."
        )
        
        # Versions for Document 1 (triggers SameVersionStrategy)
        self.v1 = KnowledgeDocumentVersion.objects.create(
            knowledge_document=self.doc1,
            version=1,
            raw_content="Version 1 body operational procedures text."
        )
        self.v2 = KnowledgeDocumentVersion.objects.create(
            knowledge_document=self.doc1,
            version=2,
            raw_content="Version 2 body operational procedures text changes."
        )

        self.doc2 = KnowledgeDocument.objects.create(
            title="Operating Procedures Document",
            current_version=1,
            repository_status="ACTIVE",
            raw_content="Variant operational procedures context."
        )
        
        # Group of records sharing entity type and department (triggers SameEntityType & SameDepartment)
        self.rec1 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc1,
            entity_type="Operator",
            canonical_data={"employee_id": "OP1", "department": "Control Room", "salary": 3000}
        )
        
        self.rec2 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc2,
            entity_type="Operator",
            canonical_data={"employee_id": "OP2", "department": "Control Room", "salary": 3200}
        )

    def test_deduplicator_bidirectional_duplicates(self):
        # A->B and B->A should generate the identical fingerprint hash
        fingerprint_ab = CandidateDeduplicator.generate_fingerprint("doc1", "seg1", "doc2", "seg2", "VersionStrategy")
        fingerprint_ba = CandidateDeduplicator.generate_fingerprint("doc2", "seg2", "doc1", "seg1", "VersionStrategy")
        
        self.assertEqual(fingerprint_ab, fingerprint_ba)
        
        # Deduplication retains the one with highest strategy confidence
        candidates = [
            {
                "source_document_id": "doc1", "source_segment_id": "seg1",
                "target_document_id": "doc2", "target_segment_id": "seg2",
                "strategy_used": "VersionStrategy", "strategy_confidence": 60.0
            },
            {
                "source_document_id": "doc2", "source_segment_id": "seg2",
                "target_document_id": "doc1", "target_segment_id": "seg1",
                "strategy_used": "VersionStrategy", "strategy_confidence": 90.0
            }
        ]
        deduplicated, count = CandidateDeduplicator.deduplicate(candidates)
        self.assertEqual(len(deduplicated), 1)
        self.assertEqual(count, 1)
        self.assertEqual(deduplicated[0]["strategy_confidence"], 90.0)

    def test_e2e_candidate_generation_orchestration(self):
        service = CandidateOrchestrationService()
        report = service.generate_candidates()
        
        # Verify Report structure parameters
        self.assertIn("batch_id", report)
        self.assertEqual(report["documents_processed"], 2)
        self.assertEqual(report["records_processed"], 2)
        self.assertGreater(report["segments_generated"], 0)
        self.assertGreater(report["candidates_persisted"], 0)
        self.assertGreater(report["execution_time"], 0.0)
        
        # Verify candidates exist in Database
        db_candidates = KnowledgeCandidate.objects.filter(batch_id=report["batch_id"])
        self.assertEqual(db_candidates.count(), report["candidates_persisted"])
        
        # Inspect model field bindings
        sample = db_candidates.first()
        self.assertIsNotNone(sample.candidate_id)
        self.assertEqual(sample.status, "GENERATED")
        self.assertIn("pipeline_version", sample.metadata)
        self.assertIn("generated_at", sample.metadata)
