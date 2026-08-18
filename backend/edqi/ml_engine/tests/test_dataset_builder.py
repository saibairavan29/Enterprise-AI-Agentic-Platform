from django.test import TestCase
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.models import EnterpriseDataQualityReport
from edqi.ml_engine.dataset_builder import DatasetBuilder
from edqi.ml_engine.exceptions import DatasetBuilderException

class DatasetBuilderTestCase(TestCase):
    def setUp(self):
        self.doc = KnowledgeDocument.objects.create(
            title="HR Ingestion Sheet",
            repository_status="ACTIVE"
        )
        self.rec1 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee"
        )
        self.rec2 = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee"
        )
        
        # Create reports
        self.report1 = EnterpriseDataQualityReport.objects.create(
            knowledge_record=self.rec1,
            overall_quality_score=95.0,
            completeness_score=100.0,
            validity_score=95.0,
            consistency_score=100.0,
            uniqueness_score=100.0,
            timeliness_score=100.0,
            quality_grade="A",
            ml_ready_features={
                "missing_fields": 0,
                "invalid_fields": 1,
                "duplicate_fields": 0,
                "record_age": 5,
                "quality_score": 95.0,
                "completeness_score": 100.0,
                "validity_score": 95.0,
                "consistency_score": 100.0,
                "uniqueness_score": 100.0,
                "timeliness_score": 100.0
            }
        )

        self.report2 = EnterpriseDataQualityReport.objects.create(
            knowledge_record=self.rec2,
            overall_quality_score=50.0,
            completeness_score=50.0,
            validity_score=50.0,
            consistency_score=50.0,
            uniqueness_score=100.0,
            timeliness_score=50.0,
            quality_grade="F",
            ml_ready_features={
                "missing_fields": 2,
                "invalid_fields": 1,
                "duplicate_fields": 0,
                "record_age": 10,
                "quality_score": 50.0,
                "completeness_score": 50.0,
                "validity_score": 50.0,
                "consistency_score": 50.0,
                "uniqueness_score": 100.0,
                "timeliness_score": 50.0
            }
        )

    def test_target_class_mapping(self):
        builder = DatasetBuilder()
        self.assertEqual(builder.get_target_class("A+"), "Excellent")
        self.assertEqual(builder.get_target_class("A"), "Excellent")
        self.assertEqual(builder.get_target_class("B"), "Good")
        self.assertEqual(builder.get_target_class("C"), "Average")
        self.assertEqual(builder.get_target_class("D"), "Average")
        self.assertEqual(builder.get_target_class("F"), "Poor")

    def test_build_dataset(self):
        builder = DatasetBuilder()
        X, y, metadata = builder.build_dataset(document_id=self.doc.id)
        
        self.assertEqual(len(X), 2)
        self.assertEqual(len(y), 2)
        self.assertEqual(y.iloc[0], "Excellent")
        self.assertEqual(y.iloc[1], "Poor")
        
        # Verify metadata fingerprinting
        self.assertIsNotNone(metadata["dataset_hash"])
        self.assertEqual(metadata["record_count"], 2)
        self.assertEqual(metadata["feature_count"], 10)
        self.assertIn("features_diagnostics", metadata)

    def test_empty_dataset_exception(self):
        import uuid
        builder = DatasetBuilder()
        with self.assertRaises(DatasetBuilderException):
            builder.build_dataset(document_id=uuid.uuid4())
