from django.test import TestCase
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.models import EnterpriseDataQualityReport, EnterpriseQualityMetrics
from edqi.ml_engine.models import TrainedModel, PredictionHistory
from edqi.ml_engine.services.training_service import TrainingService
from edqi.ml_engine.services.prediction_service import PredictionService
from edqi.ml_engine.repositories.training_repository import TrainingRepository
from repository.signals import repository_sync_completed

class EndToEndPipelineTestCase(TestCase):
    def setUp(self):
        # Create a document
        self.doc = KnowledgeDocument.objects.create(
            title="E2E Pipeline Ingestion Sheet",
            repository_status="ACTIVE"
        )
        
        # Create 20 mock records to satisfy Stratified 5-Fold cross-validation split (requires min 5 samples per class)
        # Class distribution: 10 clean (Excellent), 10 dirty (Poor)
        for i in range(1, 11):
            KnowledgeRecord.objects.create(
                knowledge_document=self.doc,
                entity_type="employee",
                canonical_data={
                    "employee_id": f"EMP{i:03d}",
                    "email": f"alice{i}@company.com",
                    "department": "HR",
                    "salary": 6500.0 + i,
                    "joining_date": "2026-08-04"
                }
            )

        for i in range(11, 21):
            KnowledgeRecord.objects.create(
                knowledge_document=self.doc,
                entity_type="employee",
                canonical_data={
                    "employee_id": f"EMP{i:03d}",
                    "email": "invalid-email-format",
                    "department": "", # Missing field
                    "salary": -100.0, # Out of range
                    "joining_date": "2026-08-04"
                }
            )

    def test_e2e_pipeline_execution(self):
        # 1. Trigger signal receiver (repository_sync_completed) to execute rule engine assessments
        # This will run batch_service and populate quality reports in DB.
        
        # Clear any existing metric objects
        EnterpriseQualityMetrics.objects.all().delete()
        EnterpriseDataQualityReport.objects.all().delete()
        
        repository_sync_completed.send(
            sender=self.__class__,
            document_id=self.doc.id,
            pipeline_id="e2e-pipeline-sync-1",
            records_count=20
        )

        # Assert reports are generated
        reports_count = EnterpriseDataQualityReport.objects.filter(knowledge_record__knowledge_document_id=self.doc.id).count()
        self.assertEqual(reports_count, 20)

        # 2. Run training service
        # This will load quality reports, build dataset, run stratified 5-fold cross validation,
        # train Random Forest & XGBoost, fit Isolation Forest, rank them, and promote the best model to ACTIVE.
        training_service = TrainingService()
        
        # Lower estimators counts temporarily for fast unit testing run
        training_service.config["random_forest"]["n_estimators"] = 5
        training_service.config["xgboost"]["n_estimators"] = 5
        training_service.config["isolation_forest"]["n_estimators"] = 5

        # Clear any old TrainedModel records
        TrainedModel.objects.all().delete()

        # Run training
        log_entry = training_service.run_training_pipeline(
            document_id=self.doc.id,
            dataset_version="v1.0.0"
        )
        
        # Assert active model is successfully created
        self.assertIsNotNone(log_entry.get("model_version"))
        active_classifier = TrainedModel.objects.filter(status='ACTIVE').exclude(algorithm='Isolation Forest').first()
        active_anomaly = TrainedModel.objects.filter(status='ACTIVE', algorithm='Isolation Forest').first()
        
        self.assertIsNotNone(active_classifier)
        self.assertIsNotNone(active_anomaly)
        self.assertTrue(active_classifier.accuracy >= 0.0)

        # 3. Run Prediction Service (Inference)
        # Verify it loads ACTIVE classifier and anomaly detector, evaluates new features,
        # maps confidence tiers, outputs probabilities, and tracks logs in PredictionHistory.
        prediction_service = PredictionService()
        
        test_features = {
            "missing_fields": 0,
            "invalid_fields": 0,
            "duplicate_fields": 0,
            "record_age": 1,
            "quality_score": 100.0,
            "completeness_score": 100.0,
            "validity_score": 100.0,
            "consistency_score": 100.0,
            "uniqueness_score": 100.0,
            "timeliness_score": 100.0
        }
        
        # Run inference
        pred_record = KnowledgeRecord.objects.filter(knowledge_document=self.doc).first()
        res = prediction_service.predict_record_quality(pred_record.id, test_features)
        
        self.assertNotEqual(res["model_version"], "RULE_FALLBACK") # Must use trained classifier
        self.assertEqual(res["predicted_grade"], "Excellent")
        self.assertIn("Excellent", res["predicted_probability"])
        self.assertIn("is_anomaly", res)
        self.assertTrue(res["prediction_time_ms"] > 0.0)
        
        # Assert history was logged in db
        hist = PredictionHistory.objects.filter(knowledge_record=pred_record).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.predicted_grade, "Excellent")
        self.assertEqual(hist.model_name, active_classifier.model_name)
