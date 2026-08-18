import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ingestion.models import Document, ProcessingHistory
from ..services.orchestration_service import IngestionOrchestrationService
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ..exceptions.orchestration_exceptions import StageExecutionException

User = get_user_model()

class IngestionOrchestrationTests(TestCase):
    """
    Orchestrator pipeline tests suite validating sequential stages registry execution,
    context tracking, postgres persistence, transaction rollbacks, and stage performance histories.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="pipeline_tester", password="Password123")
        self.service = IngestionOrchestrationService()
        
        # Set up a raw text mock document payload
        self.txt_content = b"Hello, this is raw text for the ingestion pipeline."
        self.txt_file = SimpleUploadedFile("test_doc.txt", self.txt_content)
        self.doc = Document.objects.create(
            uploaded_by=self.user,
            file=self.txt_file,
            file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            original_name="test_doc.txt",
            file_size=len(self.txt_content),
            mime_type="text/plain",
            parser_type="TEXT"
        )

    def test_e2e_successful_pipeline_execution(self):
        """
        Verify successful end-to-end execution of all registered stages,
        Postgres updates, and history logs database insertions.
        """
        res = self.service.process_document(self.doc.id, self.user)
        
        self.assertTrue(res["success"])
        self.assertEqual(res["processing_status"], "COMPLETED")
        self.assertGreater(res["pipeline_duration"], 0.0)

        # Assert stage report statuses
        stages = res["stage_execution"]
        self.assertEqual(stages["Validation"]["status"], "SUCCESS")
        self.assertEqual(stages["Parser"]["status"], "SUCCESS")
        self.assertEqual(stages["OCR"]["status"], "SKIPPED")
        self.assertEqual(stages["Metadata"]["status"], "SUCCESS")
        self.assertEqual(stages["SchemaMapping"]["status"], "SUCCESS")
        self.assertEqual(stages["Standardization"]["status"], "SUCCESS")
        self.assertEqual(stages["Persistence"]["status"], "SUCCESS")

        # Verify Document database states updates
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.processing_status, "COMPLETED")
        self.assertIsNotNone(self.doc.metadata)
        self.assertIsNotNone(self.doc.standardized_record)

        # Assert ProcessingHistory records exist in PostgreSQL
        histories = ProcessingHistory.objects.filter(document=self.doc)
        self.assertEqual(histories.count(), 7)
        
        names = [h.stage_name for h in histories]
        self.assertIn("Validation", names)
        self.assertIn("Persistence", names)

    def test_pipeline_transactional_rollback_on_failure(self):
        """
        Verify that database updates roll back on intermediate stage failures,
        while updating Document state to FAILED outside the transaction block.
        """
        # Set invalid parser type to trigger a strategy resolution failure
        self.doc.parser_type = "INVALID"
        self.doc.save()
            
        res = self.service.process_document(self.doc.id, self.user)
        
        self.assertFalse(res["success"])
        self.assertEqual(res["processing_status"], "FAILED")

        # Verify Document status resolves to FAILED
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.processing_status, "FAILED")
        
        # Verify database history entries rolled back
        histories = ProcessingHistory.objects.filter(document=self.doc)
        self.assertEqual(histories.count(), 0)

        # Verify Document payload fields remain empty
        self.assertIsNone(self.doc.metadata)
        self.assertIsNone(self.doc.standardized_record)
