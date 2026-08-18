from abc import ABC, abstractmethod
import numpy as np

class BaseExplainer(ABC):
    """
    Abstract interface for all model explanation and feature attribution engines.
    """
    @abstractmethod
    def explain(self, model, X_input: np.ndarray, feature_names: list) -> dict:
        """
        Computes feature attributions.
        Returns a dictionary containing:
        - raw_shap_values: dict mapping feature names to floats
        - base_value: float (expected model output value)
        - predicted_probability: list or float
        - explainer_name: str
        - explainer_version: str
        """
        pass
