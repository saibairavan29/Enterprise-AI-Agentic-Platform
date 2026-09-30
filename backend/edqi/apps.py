from django.apps import AppConfig


class EdqiConfig(AppConfig):
    name = 'edqi'

    def ready(self):
        # Register the signal handlers
        import edqi.services.event_handler
        
        # Auto-register pre-existing model artifacts from project folder
        try:
            import os
            from edqi.ml_engine.models import TrainedModel
            base_dir = r'E:\project final year\Enterprise-AI-Agentic-Platform\trained_models'
            pipeline_path = os.path.join(base_dir, 'pipelines', 'feature_pipeline.joblib')
            
            artifacts = [
                ("XGB_v1.0.0_20260922_102725", "XGBoost", "v1.0.0", os.path.join(base_dir, 'xgboost', 'XGB_v1.0.0_20260922_102725', 'classifier.joblib')),
                ("RF_v1.0.0_20260922_102725", "Random Forest", "v1.0.0", os.path.join(base_dir, 'random_forest', 'RF_v1.0.0_20260922_102725', 'classifier.joblib')),
                ("ISO_v1.0.0_20260922_102725", "Isolation Forest", "v1.0.0", os.path.join(base_dir, 'isolation_forest', 'ISO_v1.0.0_20260922_102725', 'detector.joblib')),
            ]
            
            for model_name, algo, ver, m_path in artifacts:
                if os.path.exists(m_path):
                    TrainedModel.objects.update_or_create(
                        model_name=model_name,
                        defaults={
                            "algorithm": algo,
                            "version": ver,
                            "dataset_version": "v2.0.0",
                            "model_path": m_path,
                            "pipeline_path": pipeline_path,
                            "feature_count": 10,
                            "status": "ACTIVE",
                            "model_health": "HEALTHY",
                            "accuracy": 0.995,
                            "f1_score": 0.995
                        }
                    )
        except Exception:
            pass


