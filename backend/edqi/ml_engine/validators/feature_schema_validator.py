import numpy as np
import pandas as pd
from edqi.ml_engine.exceptions import DatasetBuilderException
from edqi.ml_engine.logging.ml_logger import MLLogger

EXPECTED_FEATURES = [
    "price_log",
    "minimum_nights_log",
    "number_of_reviews_log",
    "reviews_per_month_filled",
    "availability_ratio",
    "host_listing_density",
    "latitude_raw",
    "longitude_raw",
    "price_to_type_zscore",
    "text_length_name"
]

class FeatureSchemaValidator:
    """
    Validates features inputs mapping names, orders, and data types before inference.
    """
    @classmethod
    def validate_features_dict(cls, features: dict):
        """
        Validates a single record features dict.
        """
        for key in EXPECTED_FEATURES:
            if key not in features:
                msg = f"Feature mismatch: missing required feature '{key}'"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
                
            val = features[key]
            if val is not None and not isinstance(val, (int, float, np.integer, np.floating)):
                msg = f"Type mismatch: feature '{key}' expected numeric, got '{type(val).__name__}'"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame):
        """
        Validates a dataset DataFrame.
        """
        missing_cols = [col for col in EXPECTED_FEATURES if col not in df.columns]
        if missing_cols:
            msg = f"DataFrame missing columns: {missing_cols}"
            MLLogger.error(msg)
            raise DatasetBuilderException(msg)
            
        for idx, col in enumerate(EXPECTED_FEATURES):
            if df.columns[idx] != col:
                msg = f"Feature order mismatch at index {idx}: expected '{col}', got '{df.columns[idx]}'"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
                
        for col in EXPECTED_FEATURES:
            if not pd.api.types.is_numeric_dtype(df[col]):
                msg = f"Column '{col}' is not numeric dtype"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
