import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from edqi.ml_engine.exceptions import PredictionException, ModelRepositoryException
from edqi.ml_engine.logging.ml_logger import MLLogger

class AnomalyDetector:
    """
    Wraps unsupervised Isolation Forest to identify outlier records.
    """
    def __init__(self, model_instance=None):
        self.model = model_instance

    def fit(self, X_scaled: np.ndarray, params: dict):
        """
        Fits the Isolation Forest on scaled features.
        """
        MLLogger.training("Fitting Isolation Forest model...")
        self.model = IsolationForest(**params)
        self.model.fit(X_scaled)
        return self

    def predict_anomaly(self, x_scaled: np.ndarray) -> tuple:
        """
        Infers whether a single record is an anomaly.
        Returns a tuple: (is_anomaly: bool, anomaly_score: float)
        """
        if self.model is None:
            raise PredictionException("Isolation Forest model is not fitted.")

        # Reshape if 1D array
        if x_scaled.ndim == 1:
            x_scaled = x_scaled.reshape(1, -1)

        # 1. Classify (-1 = anomaly, 1 = normal)
        pred = self.model.predict(x_scaled)[0]
        is_anomaly = bool(pred == -1)

        # 2. Compute anomaly score
        # decision_function outputs values where lower indicates more anomalous.
        # Opposing it returns higher values for higher anomalies.
        score = float(-self.model.decision_function(x_scaled)[0])

        return is_anomaly, round(score, 4)

    def save_model(self, path: str):
        """
        Saves Isolation Forest model to path.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            joblib.dump(self.model, path)
            MLLogger.info(f"Isolation Forest model saved to {path}")
        except Exception as e:
            msg = f"Failed to save anomaly detector: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)

    @classmethod
    def load_model(cls, path: str):
        """
        Loads Isolation Forest model.
        """
        if not os.path.exists(path):
            raise ModelRepositoryException(f"Isolation Forest model not found at: {path}")
        try:
            model_instance = joblib.load(path)
            MLLogger.info(f"Loaded Isolation Forest model from {path}")
            return cls(model_instance=model_instance)
        except Exception as e:
            msg = f"Failed to load anomaly detector: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)
