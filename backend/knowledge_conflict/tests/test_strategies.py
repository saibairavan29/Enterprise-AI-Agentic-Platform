from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from ingestion.models import Document
from repository.models import KnowledgeDocument, KnowledgeDocumentVersion, KnowledgeRecord
from ..registry.strategy_registry import StrategyRegistry
from ..candidates.strategies import (
    SameVersionStrategy,
    SameEntityTypeStrategy,
    SameDepartmentStrategy,
    SameTitleStrategy,
    SimilarityWindowStrategy
)

User = get_user_model()

class StrategiesTests(TestCase):
    """
    Test suite validating candidate pair generations across the 5 configured strategies.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="strat_tester", email="strat_tester@example.com", password="Password123")
        self.txt_file = SimpleUploadedFile("mock.txt", b"Mock content.")
        
        self.raw_doc = Document.objects.create(
            uploaded_by=self.user,
            file=self.txt_file,
            file_hash="hash001",
            original_name="mock.txt",
            file_size=10,
            mime_type="text/plain",
            parser_type="TEXT"
        )
        
        # Document 1 (v2)
        self.doc1 = KnowledgeDocument.objects.create(
            source_document=self.raw_doc,
            title="Standard Operations Procedure",
            current_version=2,
            repository_status="ACTIVE",
            raw_content="Active operational procedures content."
        )
        
        # Versions for Document 1
        self.v1 = KnowledgeDocumentVersion.objects.create(
            knowledge_document=self.doc1,
            version=1,
            raw_content="Version 1 operational procedures context."
        )
        self.v2 = KnowledgeDocumentVersion.objects.create(
            knowledge_document=self.doc1,
            version=2,
            raw_content="Version 2 operational procedures mismatch."
        )
        
        # Document 2 (Same Title, different doc reference to compare)
        self.doc2 = KnowledgeDocument.objects.create(
            title="Standard Operations Procedure",
            current_version=1,
            repository_status="ACTIVE",
            raw_content="Different operational procedures details."
        )
        
        # Records with entity types, departments, and salaries
        self.rec1 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc1,
            entity_type="Staff",
            canonical_data={"employee_id": "E1", "department": "HR", "salary": 4500.0}
        )
        
        self.rec2 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc2,
            entity_type="Staff",
            canonical_data={"employee_id": "E1", "department": "HR", "salary": 4800.0}
        )
        
        self.rec3 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc2,
            entity_type="Staff",
            canonical_data={"employee_id": "E3", "department": "Finance", "salary": 6500.0}
        )

        # Mock segment dictionaries
        self.segments = [
            {
                "segment_id": f"rec-{self.rec1.id}-full",
                "text": "Entity Type: Staff | employee_id: E1 | department: HR | salary: 4500.0",
                "type": "record",
                "page": None,
                "section": "Structured Record",
                "metadata": {"record_id": str(self.rec1.id), "entity_type": "Staff"}
            },
            {
                "segment_id": f"rec-{self.rec2.id}-full",
                "text": "Entity Type: Staff | employee_id: E1 | department: HR | salary: 4800.0",
                "type": "record",
                "page": None,
                "section": "Structured Record",
                "metadata": {"record_id": str(self.rec2.id), "entity_type": "Staff"}
            },
            {
                "segment_id": f"rec-{self.rec3.id}-full",
                "text": "Entity Type: Staff | employee_id: E3 | department: Finance | salary: 6500.0",
                "type": "record",
                "page": None,
                "section": "Structured Record",
                "metadata": {"record_id": str(self.rec3.id), "entity_type": "Staff"}
            },
            {
                "segment_id": f"{self.doc1.id}-para-1",
                "text": "Active operational procedures content.",
                "type": "paragraph",
                "page": 1,
                "section": "Main",
                "metadata": {}
            },
            {
                "segment_id": f"{self.doc2.id}-para-1",
                "text": "Different operational procedures details.",
                "type": "paragraph",
                "page": 1,
                "section": "Main",
                "metadata": {}
            }
        ]

    def test_same_version_strategy(self):
        strategy = SameVersionStrategy({"confidence": 100})
        pairs = strategy.generate_pairs([self.doc1], [], [])
        
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0]["strategy_used"], "SameVersionStrategy")
        self.assertEqual(pairs[0]["source_segment_id"], f"{self.doc1.id}-v1-para-1")
        self.assertEqual(pairs[0]["target_segment_id"], f"{self.doc1.id}-v2-para-1")
        self.assertEqual(pairs[1]["source_segment_id"], f"{self.doc1.id}-v1-para-1-sent-1")
        self.assertEqual(pairs[1]["target_segment_id"], f"{self.doc1.id}-v2-para-1-sent-1")
        self.assertEqual(pairs[0]["strategy_confidence"], 100)

    def test_same_entity_type_strategy(self):
        strategy = SameEntityTypeStrategy({"confidence": 90})
        pairs = strategy.generate_pairs([], [self.rec1, self.rec2, self.rec3], self.segments)
        
        # Only (rec1, rec2) pairs now since E1 == E1. rec3 (E3) is skipped.
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["strategy_used"], "SameEntityTypeStrategy")
        self.assertEqual(pairs[0]["entity_type"], "Staff")

    def test_same_department_strategy(self):
        strategy = SameDepartmentStrategy({"confidence": 90})
        pairs = strategy.generate_pairs([], [self.rec1, self.rec2, self.rec3], self.segments)
        
        # Only rec1 and rec2 are in department HR and have same employee_id E1
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["strategy_used"], "SameDepartmentStrategy")
        self.assertEqual(pairs[0]["metadata"]["department"], "HR")

    def test_same_title_strategy(self):
        strategy = SameTitleStrategy({"confidence": 75})
        pairs = strategy.generate_pairs([self.doc1, self.doc2], [], self.segments)
        
        # doc1 and doc2 share the same title "Standard Operations Procedure"
        # Pairs their paragraphs (doc1-para-1 vs doc2-para-1)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["strategy_used"], "SameTitleStrategy")

    def test_similarity_window_strategy(self):
        strategy = SimilarityWindowStrategy({"confidence": 60, "numeric_fields": {"salary": {"window": 1000.0}}})
        pairs = strategy.generate_pairs([], [self.rec1, self.rec2, self.rec3], self.segments)
        
        # rec1 ($4500) vs rec2 ($4800) diff is $300 (<= 1000 window). rec3 is $6500 (out of window).
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["strategy_used"], "SimilarityWindowStrategy")
        self.assertEqual(pairs[0]["metadata"]["difference"], 300.0)

    def test_different_employee_ids_prevent_pairing(self):
        strategy = SameEntityTypeStrategy({"confidence": 90})
        # Try pairing E1 (rec1) with E3 (rec3)
        test_segs = [s for s in self.segments if s["metadata"].get("record_id") in [str(self.rec1.id), str(self.rec3.id)]]
        pairs = strategy.generate_pairs([], [self.rec1, self.rec3], test_segs)
        self.assertEqual(len(pairs), 0)
