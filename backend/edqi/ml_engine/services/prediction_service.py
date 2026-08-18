import time
import pandas as pd
import numpy as np
from datetime import datetime
from django.utils import timezone
from edqi.ml_engine.exceptions import PredictionException
from edqi.ml_engine.logging.ml_logger import MLLogger
from edqi.ml_engine.models import PredictionHistory, TrainedModel
from edqi.ml_engine.validators.feature_schema_validator import FeatureSchemaValidator, EXPECTED_FEATURES
from edqi.ml_engine.repositories.model_repository import ModelRepository
from edqi.ml_engine.repositories.prediction_repository import PredictionRepository
from edqi.ml_engine.repositories.training_repository import TrainingRepository
from edqi.ml_engine.feature_pipeline import FeaturePipeline
from edqi.ml_engine.anomaly_detector import AnomalyDetector
from edqi.ml_engine.training_engine import REV_CLASS_MAP, CLASS_MAP
from repository.models import KnowledgeRecord

class PredictionService:
    """
    Exposes interfaces for quality grade classification and anomaly detection inference, 
    verifying model compatibility and executing rule fallbacks on validation failures.
    """
    def __init__(self):
        self.training_repo = TrainingRepository()
        self.prediction_repo = PredictionRepository()

    def _get_confidence_level(self, prob: float) -> str:
        """
        Maps numeric probability to discrete confidence level tiers.
        """
        if prob >= 0.95:
            return 'VERY_HIGH'
        elif prob >= 0.85:
            return 'HIGH'
        elif prob >= 0.70:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _execute_rule_fallback(self, record_id: int, clean_features: dict, reason: str) -> dict:
        """
        Executes fallback rule-based predictions when ML models are missing or incompatible.
        """
        start_time = time.time()
        MLLogger.warning(f"Executing rule-based fallback prediction (Reason: {reason})")

        quality_score = float(clean_features.get("quality_score", 100.0))
        
        # Map quality score back to the 4 categories
        if quality_score >= 90.0:
            grade = 'Excellent'
        elif quality_score >= 80.0:
            grade = 'Good'
        elif quality_score >= 60.0:
            grade = 'Average'
        else:
            grade = 'Poor'

        prob_dist = {
            'Excellent': 1.0 if grade == 'Excellent' else 0.0,
            'Good': 1.0 if grade == 'Good' else 0.0,
            'Average': 1.0 if grade == 'Average' else 0.0,
            'Poor': 1.0 if grade == 'Poor' else 0.0
        }

        duration_ms = (time.time() - start_time) * 1000.0

        # Record Prediction Metrics (Fallback)
        from edqi.metrics.metrics_service import MetricsService
        try:
            MetricsService.record_metric("prediction", "prediction_time_ms", duration_ms)
            MetricsService.record_metric("prediction", "confidence_score", 1.0)
            MetricsService.record_metric("prediction", "is_anomaly", 0.0)
        except Exception:
            pass

        rec_obj = KnowledgeRecord.objects.filter(pk=record_id).first()

        import hashlib
        import json
        features_json = json.dumps(clean_features, sort_keys=True)
        feature_hash = hashlib.sha256(features_json.encode('utf-8')).hexdigest()

        prediction_record = PredictionHistory(
            knowledge_record=rec_obj,
            predicted_grade=grade,
            predicted_probability=prob_dist,
            is_anomaly=False,
            anomaly_score=0.0,
            model_name="RULE_FALLBACK",
            algorithm="Rule Engine",
            model_version="1.0.0",
            dataset_version="v1.0.0",
            feature_version="1.0",
            input_feature_hash=feature_hash,
            feature_schema_version="1.0",
            pipeline_version="1.0",
            prediction_source="Rule Engine",
            prediction_time_ms=round(duration_ms, 2),
            confidence_level="VERY_HIGH",
            execution_trace={
                "fallback_reason": reason,
                "input_features": clean_features
            }
        )
        self.prediction_repo.save_prediction(prediction_record)

        return {
            "predicted_grade": grade,
            "predicted_probability": prob_dist,
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "confidence_score": 1.0,
            "confidence_level": "VERY_HIGH",
            "model_version": "RULE_FALLBACK",
            "prediction_time_ms": round(duration_ms, 2)
        }

    def predict_record_quality(self, record_id: int, ml_ready_features: dict) -> dict:
        """
        Orchestrates prediction flow: compatibility check, schema validation, 
        preprocessing, supervised grade predictions, unsupervised anomaly checks, 
        and persistence.
        """
        start_time = time.time()
        
        # Extract features and filter out metadata keys
        clean_features = {k: v for k, v in ml_ready_features.items() if k != "feature_names"}

        # 1. Retrieve active models
        active_model = self.training_repo.get_active_classifier()
        active_anomaly = self.training_repo.get_active_anomaly_detector()

        if not active_model or not active_anomaly:
            return self._execute_rule_fallback(
                record_id, clean_features, 
                "No ACTIVE classification or anomaly models registered."
            )

        # 2. Compatibility Checks
        # Validate schema length
        if active_model.feature_count != len(clean_features):
            return self._execute_rule_fallback(
                record_id, clean_features, 
                f"Feature count mismatch: model expects {active_model.feature_count}, got {len(clean_features)}."
            )

        # 3. Schema Validation
        try:
            FeatureSchemaValidator.validate_features_dict(clean_features)
        except Exception as e:
            return self._execute_rule_fallback(
                record_id, clean_features, 
                f"Features schema validation failed: {str(e)}"
            )

        try:
            # 4. Load Preprocessing Pipeline
            pipeline = FeaturePipeline.load_pipeline(active_model.pipeline_path)
            
            # Format inputs to DataFrame matching column orders
            input_df = pd.DataFrame([clean_features])[EXPECTED_FEATURES]
            scaled_features = pipeline.transform(input_df)

            # 5. Supervised quality classification
            classifier = ModelRepository.load_estimator(active_model.model_path)
            
            # Get target classes mapping list
            classes = active_model.training_configuration.get("classes", ["Excellent", "Good", "Average", "Poor"])

            pred_encoded = int(classifier.predict(scaled_features)[0])
            prob_dist = classifier.predict_proba(scaled_features)[0]

            predicted_grade = classes[pred_encoded] if pred_encoded < len(classes) else "Unknown"
            confidence_score = float(prob_dist[pred_encoded])
            confidence_level = self._get_confidence_level(confidence_score)

            # Build probability distribution dictionary
            prob_dist_dict = {}
            for idx, prob in enumerate(prob_dist):
                class_label = classes[idx] if idx < len(classes) else f"Class_{idx}"
                prob_dist_dict[class_label] = round(float(prob), 4)

            # 6. Unsupervised anomaly detection
            detector_model = ModelRepository.load_estimator(active_anomaly.model_path)
            is_anomaly, anomaly_score = AnomalyDetector(detector_model).predict_anomaly(scaled_features)

            duration_ms = (time.time() - start_time) * 1000.0

            # Record Prediction Metrics
            from edqi.metrics.metrics_service import MetricsService
            try:
                MetricsService.record_metric("prediction", "prediction_time_ms", duration_ms)
                MetricsService.record_metric("prediction", "confidence_score", confidence_score)
                MetricsService.record_metric("prediction", "is_anomaly", 1.0 if is_anomaly else 0.0)
            except Exception:
                pass

            # 7. Database Persistence
            rec_obj = KnowledgeRecord.objects.filter(pk=record_id).first()
            
            import hashlib
            import json
            features_json = json.dumps(clean_features, sort_keys=True)
            feature_hash = hashlib.sha256(features_json.encode('utf-8')).hexdigest()

            prediction_record = PredictionHistory(
                knowledge_record=rec_obj,
                predicted_grade=predicted_grade,
                predicted_probability=prob_dist_dict,
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                model_name=active_model.model_name,
                algorithm=active_model.algorithm,
                model_version=active_model.version,
                dataset_version=active_model.dataset_version,
                feature_version="1.0",
                input_feature_hash=feature_hash,
                feature_schema_version="1.0",
                pipeline_version="1.0",
                prediction_source=active_model.algorithm,
                prediction_time_ms=round(duration_ms, 2),
                confidence_level=confidence_level,
                execution_trace={
                    "model_score": active_model.accuracy,
                    "pipeline_path": active_model.pipeline_path,
                    "input_features": clean_features
                }
            )
            self.prediction_repo.save_prediction(prediction_record)

            # Increment TrainedModel prediction count and update last prediction timestamp
            active_model.prediction_count += 1
            active_model.last_prediction_at = timezone.now()
            active_model.save()

            active_anomaly.prediction_count += 1
            active_anomaly.last_prediction_at = timezone.now()
            active_anomaly.save()

            MLLogger.prediction(f"Record {record_id} successfully classified: {predicted_grade} ({confidence_level})")

            return {
                "predicted_grade": predicted_grade,
                "predicted_probability": prob_dist_dict,
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "confidence_score": round(confidence_score, 4),
                "confidence_level": confidence_level,
                "model_version": active_model.model_name,
                "prediction_time_ms": round(duration_ms, 2)
            }

        except Exception as e:
            MLLogger.exception("ML prediction execution crashed", e)
            return self._execute_rule_fallback(
                record_id, clean_features, 
                f"ML prediction execution failure: {str(e)}"
            )
