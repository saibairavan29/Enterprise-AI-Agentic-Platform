# Explainability Module (SHAP Integration Interface) - Phase 4 Milestone 3

This module serves as a placeholder stub for **Phase 4 Milestone 3: Explainable AI**. 

## Future SHAP Integration Guidelines

When implementing SHAP in Milestone 3, adhere to the following interface:

### 1. Explainability Service Interface

Create `backend/edqi/ml_engine/explainability/shap_explainer.py` exposing:

```python
class SHAPExplainerService:
    """
    Computes local and global feature attributions for trained models.
    """
    def __init__(self, model_record_name: str):
        # Load the active TrainedModel model_path and pipeline_path
        pass

    def explain_record_prediction(self, clean_features: dict) -> dict:
        """
        Computes local SHAP explanation values for a single record inference.
        Returns feature contribution mappings: {feature_name: shap_value}
        """
        pass

    def generate_summary_plot_data(self, dataset_X: pd.DataFrame) -> dict:
        """
        Generates global SHAP summary statistics (base values, mean absolute SHAP values).
        Useful for visualization on the Dashboard.
        """
        pass
```

### 2. TrainedModel explainability flag checks
- Before running the SHAP explainer, check if the model's DB record has `supports_explainability = True`.
- Random Forest and XGBoost classifiers support tree explainability out of the box using `shap.TreeExplainer`.
- Isolation Forest anomaly detector can use kernel or model-specific shap methods if supported.
