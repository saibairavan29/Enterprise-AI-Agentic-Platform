import numpy as np

class FeatureContributionBuilder:
    """
    Ranks feature attributions, normalizes contribution percentages, 
    and groups positive and negative explainability vectors.
    """
    @classmethod
    def process_contributions(cls, raw_shap: dict) -> dict:
        """
        Sorts, normalizes, and groups positive and negative feature contributions.
        Returns a dictionary containing:
        - normalized_shap_values: dict mapping feature -> float (percentage)
        - top_positive_features: list of dicts [{"feature": "...", "val": 0.2, "pct": 40}]
        - top_negative_features: list of dicts
        - absolute_importance: list of dicts [{"feature": "...", "val": 0.2}]
        """
        # 1. Separate positive and negative attributions
        positives = []
        negatives = []
        absolute_imp = []
        
        total_abs_shap = sum(abs(v) for v in raw_shap.values())
        if total_abs_shap == 0.0:
            total_abs_shap = 1.0 # Avoid division by zero

        # Normalized values (percentage contribution to total impact)
        normalized_shap = {}
        
        for feat, val in raw_shap.items():
            pct = (abs(val) / total_abs_shap) * 100.0
            normalized_shap[feat] = round(pct, 2)
            
            item = {
                "feature": feat,
                "value": round(val, 6),
                "percentage": round(pct, 2)
            }
            
            absolute_imp.append({
                "feature": feat,
                "value": round(abs(val), 6)
            })

            if val >= 0:
                positives.append(item)
            else:
                negatives.append(item)

        # Sort absolute importances
        absolute_imp = sorted(absolute_imp, key=lambda x: x["value"], reverse=True)

        # Sort positive and negative contributions by absolute magnitude
        pos_sorted = sorted(positives, key=lambda x: abs(x["value"]), reverse=True)
        neg_sorted = sorted(negatives, key=lambda x: abs(x["value"]), reverse=True)

        # Top 10 lists
        top_positive = pos_sorted[:10]
        top_negative = neg_sorted[:10]

        return {
            "normalized_shap_values": normalized_shap,
            "top_positive_features": top_positive,
            "top_negative_features": top_negative,
            "absolute_importance": absolute_imp
        }
