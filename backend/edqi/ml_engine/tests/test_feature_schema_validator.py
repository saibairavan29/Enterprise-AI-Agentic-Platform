import pandas as pd
from django.test import TestCase
from edqi.ml_engine.validators.feature_schema_validator import FeatureSchemaValidator
from edqi.ml_engine.exceptions import DatasetBuilderException

class FeatureSchemaValidatorTestCase(TestCase):
    def setUp(self):
        self.clean_features = {
            "missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0,
            "record_age": 10, "quality_score": 90.0, "completeness_score": 100.0,
            "validity_score": 100.0, "consistency_score": 100.0, "uniqueness_score": 100.0,
            "timeliness_score": 100.0
        }

    def test_validate_clean_features(self):
        # Should run without raising any exceptions
        FeatureSchemaValidator.validate_features_dict(self.clean_features)

    def test_missing_feature_raises_exception(self):
        dirty = self.clean_features.copy()
        del dirty["quality_score"]
        with self.assertRaises(DatasetBuilderException):
            FeatureSchemaValidator.validate_features_dict(dirty)

    def test_invalid_type_raises_exception(self):
        dirty = self.clean_features.copy()
        dirty["record_age"] = "not-a-number"
        with self.assertRaises(DatasetBuilderException):
            FeatureSchemaValidator.validate_features_dict(dirty)

    def test_validate_dataframe(self):
        df = pd.DataFrame([self.clean_features])
        # Columns in order
        FeatureSchemaValidator.validate_dataframe(df)

        # Mismatch order raises error
        df_shuffled = df[["timeliness_score"] + list(self.clean_features.keys())[:-1]]
        with self.assertRaises(DatasetBuilderException):
            FeatureSchemaValidator.validate_dataframe(df_shuffled)
