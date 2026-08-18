from django.test import TestCase
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.models import EnterpriseDataQualityReport, EnterpriseDatasetProfile, EnterpriseQualityMetrics
from edqi.repositories.quality_repository import QualityRepository
from edqi.repositories.profile_repository import ProfileRepository
from edqi.repositories.metrics_repository import MetricsRepository

class RepositoriesTestCase(TestCase):
    def setUp(self):
        self.doc = KnowledgeDocument.objects.create(
            title="Repo Test Document",
            repository_status="ACTIVE"
        )
        self.rec = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee"
        )
        
        self.quality_repo = QualityRepository()
        self.profile_repo = ProfileRepository()
        self.metrics_repo = MetricsRepository()

    def test_quality_repository_operations(self):
        # Create and save a quality report
        report = EnterpriseDataQualityReport(
            knowledge_record=self.rec,
            overall_quality_score=90.0,
            completeness_score=100.0,
            validity_score=100.0,
            consistency_score=100.0,
            uniqueness_score=100.0,
            timeliness_score=100.0,
            quality_grade="A"
        )
        self.quality_repo.save_report(report)
        self.assertIsNotNone(report.pk)

        # Retrieve report
        retrieved = self.quality_repo.get_report_by_uuid(report.report_id)
        self.assertEqual(retrieved.overall_quality_score, 90.0)

    def test_profile_repository_operations(self):
        # Create and save a profile
        profile = EnterpriseDatasetProfile(
            knowledge_document=self.doc,
            document_statistics={"total_records": 100},
            field_profiles={"salary": {"datatype": "Float"}}
        )
        self.profile_repo.save_profile(profile)
        self.assertIsNotNone(profile.pk)

        # Retrieve profile
        retrieved = self.profile_repo.get_profile_by_document_id(self.doc.id)
        self.assertEqual(retrieved.document_statistics["total_records"], 100)

    def test_metrics_repository_operations(self):
        # Create and save metrics
        metrics = EnterpriseQualityMetrics(
            knowledge_document=self.doc,
            batch_id="metrics-batch-1",
            record_count=100,
            average_score=92.5
        )
        self.metrics_repo.save_metrics(metrics)
        self.assertIsNotNone(metrics.pk)

        # Retrieve metrics
        retrieved = self.metrics_repo.get_metrics_by_batch_id("metrics-batch-1")
        self.assertEqual(retrieved.average_score, 92.5)
