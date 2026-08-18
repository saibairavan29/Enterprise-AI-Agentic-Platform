from edqi.ml_engine.repositories.training_repository import TrainingRepository
from edqi.ml_engine.logging.ml_logger import MLLogger

class EvaluationService:
    """
    Exposes interfaces for querying currently active model metrics, 
    diagnostics parameters, and feature importances.
    """
    def __init__(self):
        self.training_repo = TrainingRepository()

    def get_active_model_details(self) -> dict:
        """
        Retrieves training characteristics for the currently promoted classifier.
        """
        active_model = self.training_repo.get_active_classifier()
        if not active_model:
            MLLogger.warning("No active classifier model registered in the database.")
            return {}

        return {
            "model_name": active_model.model_name,
            "version": active_model.version,
            "algorithm": active_model.algorithm,
            "dataset_version": active_model.dataset_version,
            "status": active_model.status,
            "model_health": active_model.model_health,
            "accuracy": active_model.accuracy,
            "precision": active_model.precision,
            "recall": active_model.recall,
            "f1_score": active_model.f1_score,
            "roc_auc": active_model.roc_auc,
            "cross_validation_score": active_model.cross_validation_score,
            "training_time_sec": active_model.training_time_sec,
            "prediction_count": active_model.prediction_count,
            "feature_count": active_model.feature_count,
            "feature_importance": active_model.feature_importance,
            "training_completed_at": active_model.training_completed_at.isoformat() if active_model.training_completed_at else None,
            "supports_explainability": active_model.supports_explainability
        }

    def get_active_anomaly_details(self) -> dict:
        """
        Retrieves configuration parameters for the active anomaly detector.
        """
        active_anomaly = self.training_repo.get_active_anomaly_detector()
        if not active_anomaly:
            MLLogger.warning("No active Isolation Forest model registered in the database.")
            return {}

        return {
            "model_name": active_anomaly.model_name,
            "algorithm": active_anomaly.algorithm,
            "dataset_version": active_anomaly.dataset_version,
            "status": active_anomaly.status,
            "model_health": active_anomaly.model_health,
            "training_completed_at": active_anomaly.training_completed_at.isoformat() if active_anomaly.training_completed_at else None,
            "prediction_count": active_anomaly.prediction_count,
            "training_configuration": active_anomaly.training_configuration
        }
