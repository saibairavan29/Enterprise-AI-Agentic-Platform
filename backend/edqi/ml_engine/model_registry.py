import logging
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier
from edqi.ml_engine.exceptions import ConfigurationException
from edqi.ml_engine.logging.ml_logger import MLLogger

class ModelRegistry:
    """
    Registry that dynamically returns model instances based on algorithm codes.
    """
    _REGISTRY = {
        "random_forest": RandomForestClassifier,
        "xgboost": XGBClassifier,
        "isolation_forest": IsolationForest
    }

    @classmethod
    def get_model(cls, algorithm: str, params: dict = None) -> object:
        """
        Instantiates a registered model with given hyperparameters.
        """
        MLLogger.info(f"Retrieving model constructor for algorithm: {algorithm}")
        model_cls = cls._REGISTRY.get(algorithm.lower().strip())
        if not model_cls:
            raise ConfigurationException(f"Algorithm '{algorithm}' is not registered in ModelRegistry.")
            
        params = params or {}
        try:
            return model_cls(**params)
        except Exception as e:
            msg = f"Failed to instantiate {algorithm} with params {params}: {str(e)}"
            MLLogger.error(msg)
            raise ConfigurationException(msg)

    @classmethod
    def register_algorithm(cls, name: str, constructor_cls: type):
        """
        Exposes interface to register custom model classes.
        """
        cls._REGISTRY[name.lower().strip()] = constructor_cls
        MLLogger.model_lifecycle(f"Registered custom algorithm '{name}' to registry.")
