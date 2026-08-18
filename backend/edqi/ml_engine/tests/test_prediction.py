from django.test import TestCase
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.ml_engine.services.prediction_service import PredictionService
from edqi.ml_engine.models import PredictionHistory

class PredictionServiceTestCase(TestCase):
    def setUp(self):
        self.doc = KnowledgeDocument.objects.create(
            title="Pred Test Sheet",
            repository_status="ACTIVE"
        )
        self.rec = KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            entity_type="employee"
        )
        self.ml_features = {
            "missing_fields": 0,
            "invalid_fields": 0,
            "duplicate_fields": 0,
            "record_age": 1,
            "quality_score": 98.0,
            "completeness_score": 100.0,
            "validity_score": 100.0,
            "consistency_score": 100.0,
            "uniqueness_score": 100.0,
            "timeliness_score": 100.0
        }
        self.prediction_service = PredictionService()

    def test_rule_fallback_is_triggered_if_no_models(self):
        # We did not register any active models in db, so prediction_service should trigger fallback
        res = self.prediction_service.predict_record_quality(self.rec.id, self.ml_features)
        
        self.assertEqual(res["model_version"], "RULE_FALLBACK")
        self.assertEqual(res["predicted_grade"], "Excellent")
        self.assertEqual(res["confidence_level"], "VERY_HIGH")
        self.assertEqual(res["confidence_score"], 1.0)
        self.assertEqual(res["anomaly_score"], 0.0)
        
        # Verify prediction history record is created in db
        hist = PredictionHistory.objects.filter(knowledge_record=self.rec).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.predicted_grade, "Excellent")
        self.assertEqual(hist.model_name, "RULE_FALLBACK")
