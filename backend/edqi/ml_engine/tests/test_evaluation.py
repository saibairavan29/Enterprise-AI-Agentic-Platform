import numpy as np
from django.test import TestCase
from sklearn.dummy import DummyClassifier
from edqi.ml_engine.evaluation_engine import EvaluationEngine

class EvaluationEngineTestCase(TestCase):
    def setUp(self):
        self.X_test = np.random.randn(10, 5)
        # 10 binary target classes (0 and 1)
        self.y_test = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    def test_evaluate_dummy_classifier(self):
        # Create a dummy model predicting always class 0
        model = DummyClassifier(strategy="most_frequent")
        model.fit(self.X_test, self.y_test)
        
        metrics = EvaluationEngine.evaluate_model(model, self.X_test, self.y_test)
        
        # Accuracy should be 0.5 (since 5 out of 10 are class 0)
        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertTrue(metrics["f1_score"] > 0.0)
        # DummyClassifier supports predict_proba, check roc_auc
        self.assertTrue(metrics["roc_auc"] >= 0.0)
        self.assertEqual(len(metrics["confusion_matrix"]), 2)
