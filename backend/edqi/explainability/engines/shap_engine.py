import numpy as np
import pandas as pd
from edqi.explainability.engines.base import BaseExplainer
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

class SHAPTreeExplainer(BaseExplainer):
    """
    Computes mathematical Shapley feature attributions using the SHAP library TreeExplainer.
    """
    def explain(self, model, X_input: np.ndarray, feature_names: list, target_class_index: int = 0) -> dict:
        """
        Executes SHAP TreeExplainer attribution.
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP package is not installed or importable on this environment.")

        ExplainabilityLogger.info("Starting SHAP TreeExplainer attribution analysis.")
        
        # 1. Initialize explainer
        # XGBoost or Scikit-Learn tree models are supported
        explainer = shap.TreeExplainer(model)
        
        # 2. Compute SHAP values
        shap_values_raw = explainer.shap_values(X_input)
        expected_value_raw = explainer.expected_value

        # 3. Extract sample values for target class index
        # Multi-class output structures typically return lists of length [classes]
        if isinstance(shap_values_raw, list):
            # Safe boundary check
            idx = min(target_class_index, len(shap_values_raw) - 1)
            shap_row = shap_values_raw[idx]
            if shap_row.ndim > 1:
                shap_vector = shap_row[0] # First sample row
            else:
                shap_vector = shap_row
        elif isinstance(shap_values_raw, np.ndarray):
            if shap_values_raw.ndim == 3: # (samples, features, classes)
                idx = min(target_class_index, shap_values_raw.shape[2] - 1)
                shap_vector = shap_values_raw[0, :, idx]
            elif shap_values_raw.ndim == 2: # (samples, features)
                shap_vector = shap_values_raw[0]
            else:
                shap_vector = shap_values_raw
        else:
            shap_vector = np.zeros(len(feature_names))

        # 4. Extract base expected value
        if isinstance(expected_value_raw, (list, np.ndarray)):
            idx = min(target_class_index, len(expected_value_raw) - 1)
            base_value = float(expected_value_raw[idx])
        else:
            base_value = float(expected_value_raw)

        # 5. Map values to feature names
        raw_attributions = {}
        for idx, name in enumerate(feature_names):
            val = float(shap_vector[idx]) if idx < len(shap_vector) else 0.0
            raw_attributions[name] = round(val, 6)

        # Predict probability if supported
        pred_prob = 1.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_input)[0]
            idx = min(target_class_index, len(probs) - 1)
            pred_prob = float(probs[idx])

        return {
            "raw_shap_values": raw_attributions,
            "base_value": round(base_value, 4),
            "predicted_probability": round(pred_prob, 4),
            "explainer_name": "SHAP TreeExplainer",
            "explainer_version": "1.0"
        }
