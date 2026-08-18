import logging
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class FeatureGenerator:
    """
    Constructs data quality feature vectors for downstream Machine Learning models.
    Supports versioning of feature spaces.
    """
    def __init__(self, feature_version="1.0"):
        self.feature_version = feature_version

    def generate_features(self, scores: dict, issues: list, record_age_days: float, overall_score: float) -> tuple:
        """
        Generates two dictionaries: quality_features and ml_ready_features.
        """
        # Count issues by type and dimension
        missing_count = sum(1 for issue in issues if issue.get("issue_type") == "MISSING_FIELD")
        invalid_count = sum(1 for issue in issues if issue.get("issue_type") in ["INVALID_FORMAT", "INVALID_RANGE", "INVALID_VALUE"])
        consistency_count = sum(1 for issue in issues if issue.get("issue_type") == "INCONSISTENT_CROSS_FIELDS")
        duplicate_count = sum(1 for issue in issues if issue.get("issue_type") == "DUPLICATE_RECORD")

        # Deduce boolean indicators
        email_valid = not any("email" in str(issue.get("field_name")).lower() for issue in issues)
        phone_valid = not any("phone" in str(issue.get("field_name")).lower() for issue in issues)
        salary_negative = any("salary" in str(issue.get("field_name")).lower() and "negative" in str(issue.get("description")).lower() for issue in issues)
        joining_after_exit = any("date" in str(issue.get("field_name")).lower() and "joining" in str(issue.get("description")).lower() for issue in issues)

        # 1. Complete rules-engine feature space
        quality_features = {
            "missing_fields": missing_count,
            "invalid_fields": invalid_count,
            "consistency_issues": consistency_count,
            "duplicate_fields": duplicate_count,
            "record_age_days": round(record_age_days, 2) if record_age_days is not None else 0.0,
            "email_valid": email_valid,
            "phone_valid": phone_valid,
            "salary_negative": salary_negative,
            "joining_after_exit": joining_after_exit
        }

        # 2. Optimized vector subset for Random Forest / XGBoost classifiers in Milestone 2
        feature_keys = [
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
        ml_ready_features = {
            "missing_fields": missing_count,
            "invalid_fields": invalid_count,
            "duplicate_fields": duplicate_count,
            "record_age": int(record_age_days) if record_age_days is not None else 0,
            "quality_score": round(overall_score, 2),
            "completeness_score": round(scores.get(DataQualityDimension.COMPLETENESS.value, 100.0), 2),
            "validity_score": round(scores.get(DataQualityDimension.VALIDITY.value, 100.0), 2),
            "consistency_score": round(scores.get(DataQualityDimension.CONSISTENCY.value, 100.0), 2),
            "uniqueness_score": round(scores.get(DataQualityDimension.UNIQUENESS.value, 100.0), 2),
            "timeliness_score": round(scores.get(DataQualityDimension.TIMELINESS.value, 100.0), 2),
            "feature_names": feature_keys
        }

        return quality_features, ml_ready_features
