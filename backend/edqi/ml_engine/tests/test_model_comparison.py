from django.test import TestCase
from edqi.ml_engine.model_comparison import ModelComparer

class ModelComparerTestCase(TestCase):
    def setUp(self):
        self.config = {
            "model_selection": {
                "strategy": "weighted_score",
                "weights": {
                    "accuracy": 0.35,
                    "f1": 0.30,
                    "roc_auc": 0.20,
                    "cross_validation": 0.10,
                    "training_time": 0.05
                }
            }
        }
        self.comparer = ModelComparer(self.config)
        
        self.metrics_rf = {
            "accuracy": 0.90, "f1_score": 0.88, "roc_auc": 0.92,
            "cross_validation_score": 0.87, "training_time_sec": 1.5
        }
        self.metrics_xgb = {
            "accuracy": 0.95, "f1_score": 0.94, "roc_auc": 0.96,
            "cross_validation_score": 0.92, "training_time_sec": 5.0
        }

    def test_weighted_score_calculation(self):
        score_rf = self.comparer.calculate_score(self.metrics_rf)
        score_xgb = self.comparer.calculate_score(self.metrics_xgb)
        
        # XGBoost should score higher because accuracy, F1, ROC, CV are higher,
        # despite having slightly higher training time
        self.assertTrue(score_xgb > score_rf)

    def test_select_best_model(self):
        candidates = [
            ("random_forest_v1", self.metrics_rf),
            ("xgboost_v1", self.metrics_xgb)
        ]
        best_tag, score = self.comparer.select_best_model(candidates)
        self.assertEqual(best_tag, "xgboost_v1")
