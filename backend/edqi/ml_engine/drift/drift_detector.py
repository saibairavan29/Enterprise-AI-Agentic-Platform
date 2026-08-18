import numpy as np
import pandas as pd
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

try:
    from scipy.stats import ks_2samp
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

class DriftDetector:
    """
    Computes statistical shifts between a baseline reference dataset and target dataset.
    """
    @classmethod
    def detect_drift(cls, baseline_df: pd.DataFrame, target_df: pd.DataFrame) -> dict:
        ExplainabilityLogger.info("Starting model drift computation.")
        drift_results = {}
        drift_count = 0
        total_features = len(baseline_df.columns)

        for col in baseline_df.columns:
            if col not in target_df.columns:
                continue

            b_vals = baseline_df[col].dropna().values
            t_vals = target_df[col].dropna().values

            if len(b_vals) == 0 or len(t_vals) == 0:
                continue

            # Compute stats
            b_mean, t_mean = float(np.mean(b_vals)), float(np.mean(t_vals))
            b_std, t_std = float(np.std(b_vals)), float(np.std(t_vals))

            mean_shift = abs(b_mean - t_mean) / max(1e-5, b_std)
            std_shift = abs(b_std - t_std) / max(1e-5, b_std)

            # Distribution drift using KS test or fallback
            p_val = 1.0
            stat = 0.0
            is_drifted = False

            if HAS_SCIPY:
                try:
                    stat, p_val = ks_2samp(b_vals, t_vals)
                    is_drifted = bool(p_val < 0.05)
                except Exception:
                    is_drifted = bool(mean_shift > 0.2)
            else:
                is_drifted = bool(mean_shift > 0.2)

            if is_drifted:
                drift_count += 1

            drift_results[col] = {
                "mean_baseline": round(b_mean, 4),
                "mean_target": round(t_mean, 4),
                "mean_shift": round(mean_shift, 4),
                "std_baseline": round(b_std, 4),
                "std_target": round(t_std, 4),
                "std_shift": round(std_shift, 4),
                "ks_statistic": round(stat, 4),
                "p_value": round(p_val, 6),
                "drift_detected": is_drifted
            }

        # Calculate dataset-wide metrics
        baseline_size = len(baseline_df)
        target_size = len(target_df)
        size_drift = abs(baseline_size - target_size) / max(1, baseline_size)

        drift_percentage = (drift_count / max(1, total_features)) * 100.0
        drift_severity = "LOW"
        suggest_retraining = False

        if drift_percentage > 50.0 or size_drift > 0.5:
            drift_severity = "HIGH"
            suggest_retraining = True
        elif drift_percentage > 20.0 or size_drift > 0.2:
            drift_severity = "MEDIUM"
            suggest_retraining = True

        return {
            "drift_percentage": round(drift_percentage, 2),
            "drift_severity": drift_severity,
            "suggest_retraining": suggest_retraining,
            "features_drift": drift_results,
            "dataset_sizes": {
                "baseline": baseline_size,
                "target": target_size,
                "drift": round(size_drift, 4)
            }
        }
