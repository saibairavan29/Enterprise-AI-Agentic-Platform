from django.test import TestCase
from django.utils import timezone
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.ml_engine.models import TrainedModel, PredictionHistory
from edqi.ml_engine.repositories.training_repository import TrainingRepository
from edqi.ml_engine.repositories.prediction_repository import PredictionRepository

class MLRepositoriesTestCase(TestCase):
    def setUp(self):
        self.training_repo = TrainingRepository()
        self.prediction_repo = PredictionRepository()
        
        self.doc = KnowledgeDocument.objects.create(
            title="Repo Test", repository_status="ACTIVE"
        )
        self.rec = KnowledgeRecord.objects.create(
            knowledge_document=self.doc, entity_type="employee"
        )

    def test_training_repository_operations(self):
        # Create models
        rf = TrainedModel.objects.create(
            model_name="RF_v1.0.0_test",
            version="1.0.0",
            algorithm="Random Forest",
            dataset_version="v1.0.0",
            status="VALIDATING",
            model_path="/dummy/path",
            pipeline_path="/dummy/path"
        )
        
        retrieved = self.training_repo.get_model_by_name("RF_v1.0.0_test")
        self.assertEqual(retrieved.algorithm, "Random Forest")

        # Promote model to active
        self.training_repo.promote_to_active("RF_v1.0.0_test")
        active = self.training_repo.get_active_classifier()
        self.assertEqual(active.model_name, "RF_v1.0.0_test")
        self.assertEqual(active.status, "ACTIVE")

    def test_prediction_repository_operations(self):
        pred = PredictionHistory.objects.create(
            knowledge_record=self.rec,
            predicted_grade="Excellent",
            model_name="RF_v1.0.0_test",
            algorithm="Random Forest",
            model_version="1.0.0",
            dataset_version="v1.0.0",
            confidence_level="HIGH"
        )
        
        res = self.prediction_repo.get_predictions_by_record(self.rec.id)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].predicted_grade, "Excellent")
