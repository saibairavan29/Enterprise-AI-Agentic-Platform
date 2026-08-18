import os
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from edqi.ml_engine.exceptions import ModelRepositoryException
from edqi.ml_engine.logging.ml_logger import MLLogger

class FeaturePipeline:
    """
    Creates and serializes scikit-learn preprocessing pipelines containing 
    median value imputers and standardization scalers.
    """
    def __init__(self):
        self.pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])

    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Fits the preprocessing pipeline on X and transforms the columns.
        Returns scaled numpy array or DataFrame.
        """
        MLLogger.info("Fitting and transforming feature space matrix.")
        scaled_features = self.pipeline.fit_transform(X)
        return scaled_features

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Applies fit pipeline onto X.
        """
        scaled_features = self.pipeline.transform(X)
        return scaled_features

    def save_pipeline(self, path: str):
        """
        Serializes pipeline state to path using joblib.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            joblib.dump(self.pipeline, path)
            MLLogger.info(f"Feature pipeline saved successfully to {path}")
        except Exception as e:
            msg = f"Failed to save feature pipeline to disk: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)

    @classmethod
    def load_pipeline(cls, path: str):
        """
        Loads serialized pipeline.
        """
        if not os.path.exists(path):
            raise ModelRepositoryException(f"Pipeline file not found: {path}")
        try:
            loaded_pipeline = joblib.load(path)
            # Create instance and attach loaded pipeline
            instance = cls()
            instance.pipeline = loaded_pipeline
            MLLogger.info(f"Loaded feature pipeline from {path}")
            return instance
        except Exception as e:
            msg = f"Failed to load pipeline from disk: {str(e)}"
            MLLogger.error(msg)
            raise ModelRepositoryException(msg)
