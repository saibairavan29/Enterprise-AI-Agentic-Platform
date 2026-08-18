import os
import json
import csv
from datetime import datetime

class FeatureHistoryService:
    """
    Manages historical tracking, MD summaries, and CSV tables of model feature importances.
    """
    @staticmethod
    def get_history_dir() -> str:
        from edqi.ml_engine.repositories.model_repository import ModelRepository
        path = os.path.join(ModelRepository.get_artifacts_dir(), "feature_history")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def record_feature_importance(cls, algorithm: str, model_version: str, dataset_version: str, feature_importance: dict, train_config: dict):
        history_dir = cls.get_history_dir()
        
        clean_algo = algorithm.replace(" ", "")
        filename = f"{clean_algo}_{model_version}.json"
        filepath = os.path.join(history_dir, filename)

        payload = {
            "model_version": model_version,
            "algorithm": algorithm,
            "dataset_version": dataset_version,
            "feature_version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "feature_importance": feature_importance,
            "training_configuration": train_config
        }

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=4)

        cls.compile_history_reports()

    @classmethod
    def compile_history_reports(cls):
        history_dir = cls.get_history_dir()
        
        files = [f for f in os.listdir(history_dir) if f.endswith(".json")]
        history_records = []
        for file in files:
            try:
                with open(os.path.join(history_dir, file), 'r') as f:
                    history_records.append(json.load(f))
            except Exception:
                pass

        history_records = sorted(history_records, key=lambda x: x.get("timestamp", ""))

        csv_path = os.path.join(history_dir, "feature_history.csv")
        all_features = set()
        for r in history_records:
            all_features.update(r.get("feature_importance", {}).keys())
        features_list = sorted(list(all_features))

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Model Version", "Algorithm", "Dataset Version", "Timestamp"] + features_list)
            for r in history_records:
                importances = r.get("feature_importance", {})
                row = [
                    r.get("model_version"),
                    r.get("algorithm"),
                    r.get("dataset_version"),
                    r.get("timestamp")
                ]
                for feat in features_list:
                    row.append(importances.get(feat, 0.0))
                writer.writerow(row)

        md_path = os.path.join(history_dir, "feature_history.md")
        md_rows = []
        for r in history_records:
            feat_rows = "\n".join(f"| {feat} | {val:.4f} |" for feat, val in sorted(r.get("feature_importance", {}).items(), key=lambda x: x[1], reverse=True)[:5])
            md_rows.append(f"""### Model: {r.get('model_version')} ({r.get('algorithm')})
- **Dataset Version:** `{r.get('dataset_version')}`
- **Timestamp:** {r.get('timestamp')}

| Feature Name | Importance Weight |
| :--- | :--- |
{feat_rows}
""")

        md_content = f"""# Historical Feature Importance Tracking Report

This document records the evolution of feature importance weights across trained estimators.

{"\n---\n\n".join(md_rows) if md_rows else "No feature histories tracked yet."}
"""
        with open(md_path, 'w') as f:
            f.write(md_content)
