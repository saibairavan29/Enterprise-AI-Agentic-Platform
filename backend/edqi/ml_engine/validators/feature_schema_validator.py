import numpy as np
import pandas as pd
from edqi.ml_engine.exceptions import DatasetBuilderException
from edqi.ml_engine.logging.ml_logger import MLLogger

EXPECTED_FEATURES = [
    "missing_fields",
    "invalid_fields",
    "duplicate_fields",
    "record_age",
    "quality_score",
    "completeness_score",
    "validity_score",
    "consistency_score",
    "uniqueness_score",
    "timeliness_score"
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
        # 1. Verify existence of required features
        for key in EXPECTED_FEATURES:
            if key not in features:
                msg = f"Feature mismatch: missing required feature '{key}'"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
                
            # 2. Check data type
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
        # 1. Verify column names
        missing_cols = [col for col in EXPECTED_FEATURES if col not in df.columns]
        if missing_cols:
            msg = f"DataFrame missing columns: {missing_cols}"
            MLLogger.error(msg)
            raise DatasetBuilderException(msg)
            
        # 2. Verify column ordering
        # Ensure column order matches EXPECTED_FEATURES exactly for predict inputs consistency
        for idx, col in enumerate(EXPECTED_FEATURES):
            if df.columns[idx] != col:
                msg = f"Feature order mismatch at index {idx}: expected '{col}', got '{df.columns[idx]}'"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
                
        # 3. Check types
        for col in EXPECTED_FEATURES:
            if not pd.api.types.is_numeric_dtype(df[col]):
                msg = f"Column '{col}' is not numeric dtype"
                MLLogger.error(msg)
                raise DatasetBuilderException(msg)
