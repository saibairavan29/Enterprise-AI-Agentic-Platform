import numpy as np
from edqi.explainability.engines.base import BaseExplainer
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

class FallbackExplainer(BaseExplainer):
    """
    Approximates feature contributions mathematically when SHAP is unavailable.
    Calculates weights using estimator feature importances and value deviations from standard baselines.
    """
    def explain(self, model, X_input: np.ndarray, feature_names: list, target_class_index: int = 0) -> dict:
        ExplainabilityLogger.fallback_used("SHAP engine not available or import failed. Initiating FallbackExplainer.")
        
        # 1. Fetch feature importances if supported, otherwise default to equal importances
        importances = np.ones(len(feature_names)) / len(feature_names)
        if hasattr(model, "feature_importances_"):
            model_importances = model.feature_importances_
            if len(model_importances) == len(feature_names):
                importances = model_importances
                
        # 2. Extract feature values from single input row
        input_row = X_input[0]
        
        # 3. Approximate Shapley values based on value deviations from optimal baselines
        # Optimal benchmarks: 
        # - score features (completeness, validity, quality...) benchmark = 100.0, average baseline = 80.0
        # - issue/count features (missing, invalid, duplicates...) benchmark = 0.0, average baseline = 0.0
        raw_shap = {}
        total_deviation = 0.0
        
        for idx, name in enumerate(feature_names):
            val = float(input_row[idx]) if idx < len(input_row) else 0.0
            importance = float(importances[idx])
            
            # Map deviation from average baseline
            if name in ["missing_fields", "invalid_fields", "duplicate_fields"]:
                # Error count features: values > 0 are negative attributions
                deviation = -float(val) * 2.0
            elif name == "record_age":
                # Stale timestamp age: age > 5 is negative attribution, bounded relative to timeliness threshold
                from edqi.rules.rules_loader import QualityRulesLoader
                rules = QualityRulesLoader.load_rules()
                timeliness_days = float(rules.get("timeliness_days", 365.0))
                if timeliness_days <= 0.0:
                    timeliness_days = 365.0
                deviation = -min(2.0, max(0.0, float(val) - 5.0) / timeliness_days)
            else:
                # Score features: val > 80 is positive, val < 80 is negative
                deviation = (float(val) - 80.0) / 100.0

            attribution = deviation * importance
            raw_shap[name] = round(attribution, 6)
            total_deviation += attribution

        # Calculate prediction probability if supported
        pred_prob = 1.0
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X_input)[0]
            idx = min(target_class_index, len(probs) - 1)
            pred_prob = float(probs[idx])

        # Baseline expected value mapping
        # Mapped to a default target score representation
        base_value = 0.65 if target_class_index in [0, 1] else 0.35

        return {
            "raw_shap_values": raw_shap,
            "base_value": base_value,
            "predicted_probability": round(pred_prob, 4),
            "explainer_name": "Fallback Explainer",
            "explainer_version": "1.0"
        }
