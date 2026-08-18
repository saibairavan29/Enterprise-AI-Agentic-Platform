import logging
from edqi.ml_engine.logging.ml_logger import MLLogger
from edqi.ml_engine.exceptions import ConfigurationException

class ModelComparer:
    """
    Ranks model candidates using a config-driven weighted selection strategy.
    """
    def __init__(self, config: dict):
        self.config = config

    def calculate_score(self, metrics: dict) -> float:
        """
        Computes selection score for a candidate's metrics dictionary.
        """
        selection_config = self.config.get("model_selection", {})
        strategy = selection_config.get("strategy", "weighted_score")
        weights = selection_config.get("weights", {
            "accuracy": 0.35,
            "f1": 0.30,
            "roc_auc": 0.20,
            "cross_validation": 0.10,
            "training_time": 0.05
        })

        if strategy != "weighted_score":
            # Default to accuracy if strategy is unrecognized
            return float(metrics.get("accuracy", 0.0))

        # Retrieve scores
        acc = metrics.get("accuracy", 0.0)
        f1 = metrics.get("f1_score", 0.0)
        roc = metrics.get("roc_auc", 0.0)
        cv = metrics.get("cross_validation_score", 0.0)
        t_time = metrics.get("training_time_sec", 0.0)

        # Map training time to a 0-1 scale (lower is better, so 1 / (1 + t_time) works perfectly)
        t_score = 1.0 / (1.0 + t_time)

        # Weighted calculation
        final_score = (
            weights.get("accuracy", 0.35) * acc +
            weights.get("f1", 0.30) * f1 +
            weights.get("roc_auc", 0.20) * roc +
            weights.get("cross_validation", 0.10) * cv +
            weights.get("training_time", 0.05) * t_score
        )

        return round(float(final_score), 4)

    def select_best_model(self, candidates: list) -> tuple:
        """
        Compares multiple model metrics and selects the best candidate.
        candidates list element: (model_name_tag, metrics_dict)
        Returns: (best_name_tag, final_score)
        """
        if not candidates:
            raise ConfigurationException("No candidate models provided for comparison.")

        best_tag = None
        best_score = -1.0

        for tag, metrics in candidates:
            score = self.calculate_score(metrics)
            MLLogger.evaluation(f"Model Candidate '{tag}' calculated selection score: {score}")
            if score > best_score:
                best_score = score
                best_tag = tag

        MLLogger.model_lifecycle(f"Model Comparison complete. Winner: '{best_tag}' (Score: {best_score})")
        return best_tag, best_score
