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

    def get_models_applicability(self, file_category: str = 'tabular') -> dict:
        """
        Determines authoritative dynamic model applicability status for:
        - Random Forest (Supervised tabular classifier)
        - XGBoost (Supervised tabular classifier)
        - Isolation Forest (Unsupervised tabular anomaly detector)
        """
        import os

        if file_category != 'tabular':
            reason_text = f"Supervised tabular classifier model is not applicable for {file_category.upper()} files."
            return {
                "random_forest": {"status": "NOT APPLICABLE", "reason": reason_text},
                "xgboost": {"status": "NOT APPLICABLE", "reason": reason_text},
                "isolation_forest": {"status": "NOT APPLICABLE", "reason": f"Unsupervised tabular anomaly detector is not applicable for {file_category.upper()} files."}
            }

        applicability = {
            "random_forest": {"status": "NOT TRAINED", "reason": "No Random Forest model registered in ML Engine."},
            "xgboost": {"status": "NOT TRAINED", "reason": "No XGBoost model registered in ML Engine."},
            "isolation_forest": {"status": "NOT TRAINED", "reason": "No Isolation Forest model registered in ML Engine."}
        }

        all_models = TrainedModel.objects.all().order_by('-created_at')

        algo_groups = {
            "random_forest": [],
            "xgboost": [],
            "isolation_forest": []
        }

        for m in all_models:
            alg_lower = m.algorithm.lower()
            if "random" in alg_lower or "rf" in alg_lower:
                algo_groups["random_forest"].append(m)
            elif "xgb" in alg_lower:
                algo_groups["xgboost"].append(m)
            elif "isolation" in alg_lower or "anomaly" in alg_lower:
                algo_groups["isolation_forest"].append(m)

        for key, models in algo_groups.items():
            if not models:
                continue

            active_model = next((m for m in models if m.status == 'ACTIVE'), None)
            if active_model:
                model_exists = os.path.exists(active_model.model_path)
                pipe_exists = os.path.exists(active_model.pipeline_path)
                if model_exists and pipe_exists:
                    applicability[key] = {
                        "status": "APPLIED",
                        "model_version": active_model.model_name,
                        "algorithm": active_model.algorithm,
                        "accuracy": active_model.accuracy,
                        "f1_score": active_model.f1_score,
                        "is_active": True
                    }
                else:
                    missing_paths = []
                    if not model_exists:
                        missing_paths.append(active_model.model_path)
                    if not pipe_exists:
                        missing_paths.append(active_model.pipeline_path)
                    applicability[key] = {
                        "status": "ARTIFACT MISSING",
                        "reason": f"Model artifact missing on disk: {', '.join(missing_paths)}",
                        "model_version": active_model.model_name
                    }
            else:
                # Models exist in registry but none is currently ACTIVE
                valid_inactive = None
                for m in models:
                    if os.path.exists(m.model_path) and os.path.exists(m.pipeline_path):
                        valid_inactive = m
                        break

                if valid_inactive:
                    applicability[key] = {
                        "status": "TRAINED / INACTIVE",
                        "reason": f"Model is trained ({valid_inactive.model_name}) but currently inactive",
                        "model_version": valid_inactive.model_name,
                        "algorithm": valid_inactive.algorithm,
                        "accuracy": valid_inactive.accuracy,
                        "f1_score": valid_inactive.f1_score,
                        "is_active": False
                    }
                else:
                    first_m = models[0]
                    applicability[key] = {
                        "status": "ARTIFACT MISSING",
                        "reason": f"Model artifact missing on disk for {first_m.model_name}",
                        "model_version": first_m.model_name
                    }

        return applicability

