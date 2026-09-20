import os
import joblib
from edqi.ml_engine.exceptions import ModelRepositoryException
from edqi.ml_engine.logging.ml_logger import MLLogger

class ModelRepository:
    """
    Handles file persistency operations for joblib model estimators and pipeline states.
    """
    @staticmethod
    def get_artifacts_dir() -> str:
        """
        Returns the absolute path to the trained_models output directory.
        """
        curr = os.path.abspath(__file__)
        for _ in range(5):
            curr = os.path.dirname(curr)
        path = os.path.join(curr, "trained_models")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def save_estimator(cls, estimator, model_name: str, filename: str) -> str:
        """
        Saves a trained model estimator using joblib.
        Returns the path to the saved file.
        """
        artifacts_dir = cls.get_artifacts_dir()
        model_dir = os.path.join(artifacts_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        file_path = os.path.join(model_dir, filename)
        try:
            joblib.dump(estimator, file_path)
            MLLogger.info(f"Estimator saved to {file_path}")
            return file_path
        except Exception as e:
            msg = f"Failed to save estimator {filename}: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)

    _model_cache = {}

    @classmethod
    def load_estimator(cls, file_path: str) -> object:
        """
        Loads a saved model estimator using joblib, cached in memory after first load.
        """
        if file_path in cls._model_cache:
            return cls._model_cache[file_path]
            
        if not os.path.exists(file_path):
            raise ModelRepositoryException(f"Estimator file not found at path: {file_path}")
        try:
            estimator = joblib.load(file_path)
            cls._model_cache[file_path] = estimator
            MLLogger.info(f"Estimator successfully loaded from {file_path} (cached in memory)")
            return estimator
        except Exception as e:
            msg = f"Failed to load estimator from {file_path}: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)
            
    @classmethod
    def get_file_size_mb(cls, file_path: str) -> float:
        """
        Calculates file size in Megabytes.
        """
        if not os.path.exists(file_path):
            return 0.0
        size_bytes = os.path.getsize(file_path)
        return float(size_bytes) / (1024.0 * 1024.0)
