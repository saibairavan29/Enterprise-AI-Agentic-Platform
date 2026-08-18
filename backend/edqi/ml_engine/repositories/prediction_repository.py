import logging
from edqi.ml_engine.models import PredictionHistory
from edqi.ml_engine.logging.ml_logger import MLLogger

class PredictionRepository:
    """
    Data access repository managing database operations for PredictionHistory models.
    """
    def save_prediction(self, prediction: PredictionHistory) -> PredictionHistory:
        """
        Saves a prediction history record.
        """
        prediction.save()
        return prediction

    def get_prediction_by_id(self, prediction_id) -> PredictionHistory:
        """
        Retrieves prediction history details by UUID.
        """
        return PredictionHistory.objects.filter(prediction_id=prediction_id).first()

    def get_predictions_by_record(self, record_id: int) -> list:
        """
        Retrieves prediction history records for a KnowledgeRecord.
        """
        return list(PredictionHistory.objects.filter(knowledge_record_id=record_id).order_by('-created_at'))

    def get_predictions_by_model(self, model_name: str) -> list:
        """
        Retrieves predictions inferred by a specific model version.
        """
        return list(PredictionHistory.objects.filter(model_name=model_name).order_by('-created_at'))
