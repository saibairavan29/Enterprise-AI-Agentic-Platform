from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ingestion.models import Document
from repository.models import KnowledgeDocument, KnowledgeRecord
from ..extractors.document_extractor import DocumentExtractor
from ..extractors.record_extractor import RecordExtractor
from ..exceptions.exceptions import ExtractorException

User = get_user_model()

class ExtractionTests(TestCase):
    """
    Test suite verifying properties and plain text extraction operations
    from KnowledgeDocument and KnowledgeRecord structures.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="extract_tester", email="extract_tester@example.com", password="Password123")
        self.txt_file = SimpleUploadedFile("mock_doc.txt", b"Mock details content payload.")
        self.raw_doc = Document.objects.create(
            uploaded_by=self.user,
            file=self.txt_file,
            file_hash="mockhash123",
            original_name="mock_doc.txt",
            file_size=100,
            mime_type="text/plain",
            parser_type="TEXT"
        )
        
        self.k_doc = KnowledgeDocument.objects.create(
            source_document=self.raw_doc,
            title="Operational Rules Document",
            current_version=2,
            repository_status="ACTIVE",
            metadata={"author": "Engineering Team", "department": "Operations"},
            raw_content="This is the main body of operational rules."
        )

        self.k_record = KnowledgeRecord.objects.create(
            knowledge_document=self.k_doc,
            entity_type="EmployeeRecord",
            canonical_data={"employee_id": "EMP001", "department": "Operations", "salary": 5000},
            additional_fields={"notes": "Standard employee record details."}
        )

    def test_document_extractor_success(self):
        extractor = DocumentExtractor()
        segments = extractor.extract(self.k_doc)
        
        # Should pull raw_content + 2 metadata strings
        self.assertEqual(len(segments), 3)
        
        raw_seg = next(s for s in segments if s["segment_id"].endswith("-raw"))
        self.assertIn("operational rules", raw_seg["text"])
        self.assertEqual(raw_seg["metadata"]["title"], "Operational Rules Document")
        self.assertEqual(raw_seg["metadata"]["version"], 2)
        
        meta_seg = next(s for s in segments if "meta-author" in s["segment_id"])
        self.assertEqual(meta_seg["text"], "author: Engineering Team")

    def test_document_extractor_raises_on_none(self):
        extractor = DocumentExtractor()
        with self.assertRaises(ExtractorException):
            extractor.extract(None)

    def test_record_extractor_success(self):
        extractor = RecordExtractor()
        segments = extractor.extract(self.k_record)
        
        # Should extract 1 full record block + 3 fields (employee_id, department, salary)
        # Note: salary is a float/int, department is str, employee_id is str
        self.assertEqual(len(segments), 4)
        
        full_seg = next(s for s in segments if s["segment_id"].endswith("-full"))
        self.assertIn("EMP001", full_seg["text"])
        self.assertIn("Operations", full_seg["text"])
        self.assertIn("notes: Standard employee record details.", full_seg["text"])
        
        field_seg = next(s for s in segments if "field-employee_id" in s["segment_id"])
        self.assertEqual(field_seg["text"], "employee_id: EMP001")
        self.assertEqual(field_seg["metadata"]["entity_type"], "EmployeeRecord")
