import numpy as np
import pandas as pd
from django.test import TestCase
from edqi.ml_engine.training_engine import TrainingEngine

class TrainingEngineTestCase(TestCase):
    def setUp(self):
        self.config = {
            "random_seed": 42,
            "train_split_ratio": 0.70,
            "val_split_ratio": 0.15,
            "test_split_ratio": 0.15,
            "random_forest": {
                "n_estimators": 5, # Low for quick test run
                "max_depth": 2,
                "random_state": 42
            },
            "xgboost": {
                "n_estimators": 5,
                "max_depth": 2,
                "learning_rate": 0.1,
                "random_state": 42
            }
        }
        
        # Build dummy features matrix with 10 features (EXPECTED_FEATURES count = 10)
        # Create 20 records to allow Stratified 5-Fold split (requires minimum 5 samples per class)
        self.X_scaled = np.random.randn(20, 10)
        self.y = pd.Series(["Excellent"] * 10 + ["Poor"] * 10)

    def test_train_random_forest(self):
        engine = TrainingEngine(self.config)
        results = engine.train_classifier("random_forest", self.X_scaled, self.y)
        
        self.assertIsNotNone(results["model"])
        self.assertTrue(results["metrics"]["accuracy"] >= 0.0)
        self.assertTrue(results["metrics"]["cross_validation_score"] >= 0.0)
        self.assertEqual(results["metrics"]["feature_count"], 10)
        self.assertTrue(len(results["feature_importance"]) > 0)

    def test_train_xgboost(self):
        engine = TrainingEngine(self.config)
        results = engine.train_classifier("xgboost", self.X_scaled, self.y)
        
        self.assertIsNotNone(results["model"])
        self.assertTrue(results["metrics"]["accuracy"] >= 0.0)
        self.assertTrue(results["metrics"]["cross_validation_score"] >= 0.0)
        self.assertEqual(results["metrics"]["feature_count"], 10)
