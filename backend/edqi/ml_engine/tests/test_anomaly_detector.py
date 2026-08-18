import numpy as np
from django.test import TestCase
from edqi.ml_engine.anomaly_detector import AnomalyDetector

class AnomalyDetectorTestCase(TestCase):
    def setUp(self):
        # Create normal training data
        self.X_train = np.random.normal(loc=0.0, scale=0.1, size=(50, 10))
        
        # Test sample (close to mean)
        self.x_normal = np.random.normal(loc=0.0, scale=0.1, size=(1, 10))
        # Test outlier (very high values)
        self.x_anomaly = np.ones((1, 10)) * 100.0

    def test_fit_predict_anomaly(self):
        detector = AnomalyDetector()
        detector.fit(self.X_train, {"contamination": 0.1, "random_state": 42})
        
        # Inliers prediction
        is_anom_norm, score_norm = detector.predict_anomaly(self.x_normal)
        # Outliers prediction
        is_anom_out, score_out = detector.predict_anomaly(self.x_anomaly)
        
        # Anomaly score for outlier should be strictly higher than inlier
        self.assertTrue(score_out > score_norm)
        self.assertTrue(is_anom_out)
