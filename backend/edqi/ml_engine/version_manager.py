import os
from django.utils import timezone
from edqi.ml_engine.models import TrainedModel
from edqi.ml_engine.history.lifecycle_history import LifecycleHistoryLogger
from edqi.ml_engine.repositories.model_repository import ModelRepository
from edqi.ml_engine.logging.ml_logger import MLLogger
import json
from datetime import datetime

class VersionManager:
    """
    Orchestrates model lifecycle transitions, rollback chains, and database-filesystem sync.
    """
    @staticmethod
    def get_manifest_path() -> str:
        curr = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(curr, "reports", "manifests")
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, "system_manifest.json")

    @classmethod
    def update_system_manifest(cls):
        path = cls.get_manifest_path()
        active_cls = TrainedModel.objects.filter(status='ACTIVE').exclude(algorithm='Isolation Forest').first()
        active_ano = TrainedModel.objects.filter(status='ACTIVE', algorithm='Isolation Forest').first()
        
        manifest = {
            "project_version": "1.0",
            "dataset_version": active_cls.dataset_version if active_cls else "v1.0.0",
            "model_version": active_cls.model_name if active_cls else "None",
            "anomaly_detector_version": active_ano.model_name if active_ano else "None",
            "rules_version": "1.0",
            "feature_version": "1.0",
            "pipeline_version": "1.0",
            "health_version": "1.0",
            "report_version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        with open(path, 'w') as f:
            json.dump(manifest, f, indent=4)

    @classmethod
    def activate_model(cls, model_name: str):
        model = TrainedModel.objects.filter(model_name=model_name).first()
        if not model:
            raise ValueError(f"TrainedModel not found: {model_name}")

        # Check files existence
        if not os.path.exists(model.model_path) or not os.path.exists(model.pipeline_path):
            raise FileNotFoundError(f"Model or Pipeline binary file not found on disk for {model_name}")

        # Deactivate current active model of same algorithm
        current_active = TrainedModel.objects.filter(status='ACTIVE', algorithm=model.algorithm).first()
        if current_active:
            if current_active.model_name == model_name:
                return # Already active
            current_active.status = 'RETIRED'
            current_active.retired_at = timezone.now()
            current_active.next_version = model.model_name
            current_active.save()
            LifecycleHistoryLogger.log_event(current_active.model_name, "RETIRED")

        # Activate model
        model.status = 'ACTIVE'
        model.activated_at = timezone.now()
        if current_active:
            model.parent_version = current_active.model_name
        model.save()
        
        LifecycleHistoryLogger.log_event(model.model_name, "ACTIVATED")
        cls.update_system_manifest()
        MLLogger.info(f"Model {model_name} activated successfully.")

    @classmethod
    def rollback_to_version(cls, model_name: str):
        model = TrainedModel.objects.filter(model_name=model_name).first()
        if not model:
            raise ValueError(f"TrainedModel not found: {model_name}")

        # Check files existence
        if not os.path.exists(model.model_path) or not os.path.exists(model.pipeline_path):
            raise FileNotFoundError(f"Binary artifacts missing on disk for rollback to {model_name}")

        # Retire the active model of the same algorithm
        active_model = TrainedModel.objects.filter(status='ACTIVE', algorithm=model.algorithm).first()
        if active_model:
            active_model.status = 'RETIRED'
            active_model.retired_at = timezone.now()
            active_model.save()
            LifecycleHistoryLogger.log_event(active_model.model_name, "RETIRED")

        # Rollback model to active
        model.status = 'ACTIVE'
        model.activated_at = timezone.now()
        model.save()

        LifecycleHistoryLogger.log_event(model.model_name, "ROLLED_BACK")
        cls.update_system_manifest()
        MLLogger.info(f"Successfully rolled back active model state to: {model_name}")

    @classmethod
    def sync_database_and_filesystem(cls):
        models = TrainedModel.objects.all()
        synced_count = 0
        failed_count = 0
        for m in models:
            if not os.path.exists(m.model_path) or not os.path.exists(m.pipeline_path):
                if m.status in ['ACTIVE', 'VALIDATING']:
                    m.status = 'FAILED'
                    m.model_health = 'DEPRECATED'
                    m.save()
                    LifecycleHistoryLogger.log_event(m.model_name, "FAILED_SYNC", {"error": "Binary artifacts missing on disk."})
                    failed_count += 1
            else:
                synced_count += 1
        return {"synced": synced_count, "failed": failed_count}

    @classmethod
    def compare_versions(cls, version_a: str, version_b: str) -> dict:
        model_a = TrainedModel.objects.filter(model_name=version_a).first()
        model_b = TrainedModel.objects.filter(model_name=version_b).first()
        if not model_a or not model_b:
            raise ValueError("One or both model versions not found for comparison.")

        return {
            "version_a": {
                "name": model_a.model_name,
                "algorithm": model_a.algorithm,
                "accuracy": model_a.accuracy,
                "precision": model_a.precision,
                "recall": model_a.recall,
                "f1_score": model_a.f1_score,
                "roc_auc": model_a.roc_auc,
                "cv_score": model_a.cross_validation_score,
                "dataset_size": model_a.training_dataset_size
            },
            "version_b": {
                "name": model_b.model_name,
                "algorithm": model_b.algorithm,
                "accuracy": model_b.accuracy,
                "precision": model_b.precision,
                "recall": model_b.recall,
                "f1_score": model_b.f1_score,
                "roc_auc": model_b.roc_auc,
                "cv_score": model_b.cross_validation_score,
                "dataset_size": model_b.training_dataset_size
            },
            "difference": {
                "accuracy": round(model_b.accuracy - model_a.accuracy, 4),
                "precision": round(model_b.precision - model_a.precision, 4),
                "recall": round(model_b.recall - model_a.recall, 4),
                "f1_score": round(model_b.f1_score - model_a.f1_score, 4),
                "roc_auc": round(model_b.roc_auc - model_a.roc_auc, 4),
                "cv_score": round(model_b.cross_validation_score - model_a.cross_validation_score, 4),
                "dataset_size": model_b.training_dataset_size - model_a.training_dataset_size
            }
        }
