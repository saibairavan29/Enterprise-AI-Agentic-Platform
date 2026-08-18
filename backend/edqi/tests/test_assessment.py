from django.test import TestCase
from django.db import transaction
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.models import EnterpriseDataQualityReport, EnterpriseDatasetProfile, EnterpriseQualityMetrics
from edqi.services.assessment_service import EnterpriseQualityAssessmentService, AssessmentContext
from edqi.services.batch_service import BatchAssessmentService
from repository.signals import repository_sync_completed

class AssessmentServicesTestCase(TestCase):
    def setUp(self):
        # Create a document
        self.doc = KnowledgeDocument.objects.create(
            title="HR Ingestion Sheet",
            repository_status="ACTIVE",
            record_count=2
        )
        
        import datetime
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        # Create record 1: clean
        self.rec1 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee",
            canonical_data={
                "employee_id": "EMP001",
                "email": "alice@company.com",
                "department": "HR",
                "salary": 6500.0,
                "joining_date": today_str
            }
        )
        
        # Create record 2: dirty (missing department, negative salary)
        self.rec2 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee",
            canonical_data={
                "employee_id": "EMP002",
                "email": "invalid-bob",
                "department": "",
                "salary": -100.0,
                "joining_date": today_str
            }
        )

    def test_single_record_assessment(self):
        service = EnterpriseQualityAssessmentService()
        context = AssessmentContext(
            pipeline_id="test-pipe-123",
            document_id=self.doc.id
        )
        
        # Assess clean record
        report1, issues1 = service.assess_record(self.rec1, context)
        self.assertEqual(report1.overall_quality_score, 100.0)
        self.assertEqual(report1.quality_grade, "A+")
        self.assertEqual(len(issues1), 0)
        
        # Assess dirty record
        report2, issues2 = service.assess_record(self.rec2, context)
        self.assertTrue(report2.overall_quality_score < 100.0)
        self.assertTrue(len(issues2) > 0)
        # Verify feature vector formats
        self.assertIn("missing_fields", report2.quality_features)
        self.assertIn("quality_score", report2.ml_ready_features)

    def test_batch_assessment_service(self):
        batch_service = BatchAssessmentService()
        metrics = batch_service.assess_document_records(
            document_id=self.doc.id,
            pipeline_id="batch-pipe-456"
        )
        
        self.assertEqual(metrics.record_count, 2)
        # Average score should be the average of report1 (100) and report2 (<100)
        self.assertTrue(metrics.average_score < 100.0)
        self.assertEqual(metrics.knowledge_document, self.doc)

        # Verify dataset profile was successfully created
        profile = EnterpriseDatasetProfile.objects.filter(knowledge_document=self.doc).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.document_statistics["total_records"], 2)

    def test_signal_event_handler(self):
        # Trigger event handler by sending signal
        # Since apps.py imports event_handler in ready(), signal should execute automatically.
        # We check that it creates metrics in the database.
        
        # Clear metrics created in setup/batch tests first
        EnterpriseQualityMetrics.objects.all().delete()
        
        repository_sync_completed.send(
            sender=self.__class__,
            document_id=self.doc.id,
            pipeline_id="signal-pipe-789",
            records_count=2
        )
        
        # Check if the metrics were saved
        metrics = EnterpriseQualityMetrics.objects.filter(knowledge_document=self.doc).first()
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.record_count, 2)
