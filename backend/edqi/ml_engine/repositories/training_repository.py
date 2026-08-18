import logging
from django.db import transaction
from edqi.ml_engine.models import TrainedModel
from edqi.ml_engine.logging.ml_logger import MLLogger

class TrainingRepository:
    """
    Data access repository managing database operations for TrainedModel models.
    """
    def save_model_record(self, model_record: TrainedModel) -> TrainedModel:
        """
        Saves or updates a TrainedModel.
        """
        model_record.save()
        return model_record

    def get_model_by_name(self, model_name: str) -> TrainedModel:
        """
        Retrieves a TrainedModel by its unique model version name.
        """
        return TrainedModel.objects.filter(model_name=model_name).first()

    def get_active_model(self) -> TrainedModel:
        """
        Retrieves the currently promoted ACTIVE model, or None if none exist.
        """
        return TrainedModel.objects.filter(status='ACTIVE').order_by('-created_at').first()

    def get_active_classifier(self) -> TrainedModel:
        """
        Retrieves active classification models.
        """
        return TrainedModel.objects.filter(status='ACTIVE').exclude(algorithm='Isolation Forest').order_by('-created_at').first()

    def get_active_anomaly_detector(self) -> TrainedModel:
        """
        Retrieves the active Isolation Forest anomaly detector.
        """
        return TrainedModel.objects.filter(status='ACTIVE', algorithm='Isolation Forest').order_by('-created_at').first()

    def promote_to_active(self, model_name: str):
        """
        Promotes a model to ACTIVE status and deactivates/retires any other active models 
        of the same algorithm.
        """
        target_model = self.get_model_by_name(model_name)
        if not target_model:
            MLLogger.error(f"Cannot promote model: '{model_name}' not found.")
            return

        is_anomaly_model = (target_model.algorithm == 'Isolation Forest')

        with transaction.atomic():
            # Retire existing active models of similar algorithm category
            if is_anomaly_model:
                TrainedModel.objects.filter(status='ACTIVE', algorithm='Isolation Forest').update(status='RETIRED')
            else:
                TrainedModel.objects.filter(status='ACTIVE').exclude(algorithm='Isolation Forest').update(status='RETIRED')
                
            # Set target model to ACTIVE
            target_model.status = 'ACTIVE'
            target_model.save()
            MLLogger.model_lifecycle(f"Successfully promoted model '{model_name}' to ACTIVE status.")

    def list_all_models(self) -> list:
        """
        Returns a list of all models.
        """
        return list(TrainedModel.objects.all().order_by('-created_at'))
