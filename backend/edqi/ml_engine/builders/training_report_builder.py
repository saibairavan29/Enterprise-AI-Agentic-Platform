import json
import os
from datetime import datetime
from edqi.ml_engine.logging.ml_logger import MLLogger

class TrainingReportBuilder:
    """
    Assembles comprehensive documentation for a model training run, 
    writing outputs to both JSON and Markdown formats.
    """
    @classmethod
    def compile_report(cls, model_metadata: dict) -> tuple:
        """
        Creates structured JSON data and formatted Markdown report.
        """
        # Create JSON report structure
        json_report = {
            "report_generated_at": datetime.utcnow().isoformat() + "Z",
            "model_metadata": model_metadata
        }

        # Create Markdown report structure
        algorithm = model_metadata.get("algorithm", "Unknown")
        model_version = model_metadata.get("model_version", "Unknown")
        dataset_version = model_metadata.get("dataset_version", "Unknown")
        dataset_hash = model_metadata.get("dataset_hash", "Unknown")
        feature_version = model_metadata.get("feature_version", "1.0")
        
        confusion_matrix = model_metadata.get("confusion_matrix", [])
        classification_report = model_metadata.get("classification_report", {})
        cv_results = model_metadata.get("cv_results", {})

        md_report = f"""# EDQI Model Training Evaluation Report

This report presents performance benchmarks, dataset diagnostics, and configuration parameters captured for the training run of the model version **{model_version}**.

---

## Model Core Metadata

| Parameter | Value |
| :--- | :--- |
| **Model Version** | `{model_version}` |
| **Algorithm** | `{algorithm}` |
| **Dataset Version** | `{dataset_version}` |
| **Feature Version** | `{feature_version}` |
| **Dataset Hash (SHA-256)** | `{dataset_hash}` |
| **Training Date** | `{model_metadata.get("training_completed_at", "Unknown")}` |
| **Total Features Count** | `{model_metadata.get("feature_count", 0)}` |

---

## Evaluation Metrics

> [!NOTE]
> Below are accuracy and F1 scores computed across test sets and Stratified K-Fold validation runs.

| Evaluation Metric | Score |
| :--- | :--- |
| **Test Accuracy** | `{round(model_metadata.get("accuracy", 0.0) * 100.0, 2)}%` |
| **Test Precision** | `{round(model_metadata.get("precision", 0.0) * 100.0, 2)}%` |
| **Test Recall** | `{round(model_metadata.get("recall", 0.0) * 100.0, 2)}%` |
| **Test F1 Score** | `{round(model_metadata.get("f1_score", 0.0) * 100.0, 2)}%` |
| **ROC AUC** | `{round(model_metadata.get("roc_auc", 0.0), 4)}` |
| **Stratified 5-Fold CV Average** | `{round(model_metadata.get("cross_validation_score", 0.0) * 100.0, 2)}%` |
| **Best CV Fold Score** | `{round(model_metadata.get("best_fold_score", 0.0) * 100.0, 2)}%` |
| **Worst CV Fold Score** | `{round(model_metadata.get("worst_fold_score", 0.0) * 100.0, 2)}%` |

---

## Training Diagnostics

- **Training Records Count:** `{model_metadata.get("training_dataset_size", 0)}`
- **Testing Records Count:** `{model_metadata.get("testing_dataset_size", 0)}`
- **Validation Records Count:** `{model_metadata.get("validation_dataset_size", 0)}`
- **Model fitting time:** `{round(model_metadata.get("training_time_sec", 0.0), 4)} seconds`
- **Model file size:** `{round(model_metadata.get("model_size_mb", 0.0), 4)} MB`
- **Explainability Supported:** `{model_metadata.get("supports_explainability", True)}`

---

## Confusion Matrix

```json
{json.dumps(confusion_matrix, indent=4)}
```

---

## Classification Report

```json
{json.dumps(classification_report, indent=4)}
```

---

## Feature Importance Rankings

The importance scores computed by the tree estimators:

```json
{json.dumps(model_metadata.get("feature_importance", {}), indent=4)}
```

---

## Cross Validation Results

```json
{json.dumps(cv_results, indent=4)}
```

---

## Training Configuration Parameters

```json
{json.dumps(model_metadata.get("training_configuration", {}), indent=4)}
```
"""
        return json_report, md_report.strip()

    @classmethod
    def save_reports(cls, model_metadata: dict, artifacts_dir: str):
        """
        Saves report.json and report.md inside the model artifacts output directory.
        """
        json_report, md_report = cls.compile_report(model_metadata)
        
        os.makedirs(artifacts_dir, exist_ok=True)
        json_path = os.path.join(artifacts_dir, "training_report.json")
        md_path = os.path.join(artifacts_dir, "training_report.md")

        try:
            with open(json_path, 'w') as f:
                json.dump(json_report, f, indent=4)
            with open(md_path, 'w') as f:
                f.write(md_report)
            MLLogger.info(f"Training reports successfully written: {json_path} and {md_path}")
        except Exception as e:
            MLLogger.error(f"Failed to save training reports: {str(e)}")
