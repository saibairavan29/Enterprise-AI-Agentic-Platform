import logging
import numpy as np
import pandas as pd
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

NON_LEAKY_FEATURE_NAMES = [
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

class FeatureGenerator:
    """
    Constructs non-leaky data quality feature vectors for downstream ML models.
    Permanently excludes composite quality scores, dimension totals, and rule-indicator flags.
    """
    def __init__(self, feature_version="2.0"):
        self.feature_version = feature_version

    @classmethod
    def extract_record_features(cls, row: dict, group_stats: dict = None) -> dict:
        """
        Extracts 10 non-leaky raw/statistical features from a record dictionary.
        """
        try:
            price = float(row.get("price") if row.get("price") is not None else 0.0)
        except (ValueError, TypeError):
            price = 0.0
        price_log = float(np.log1p(max(0.0, price)))

        try:
            min_nights = float(row.get("minimum_nights") if row.get("minimum_nights") is not None else 1.0)
        except (ValueError, TypeError):
            min_nights = 1.0
        minimum_nights_log = float(np.log1p(max(0.0, min_nights)))

        try:
            num_reviews = float(row.get("number_of_reviews") if row.get("number_of_reviews") is not None else 0.0)
        except (ValueError, TypeError):
            num_reviews = 0.0
        number_of_reviews_log = float(np.log1p(max(0.0, num_reviews)))

        try:
            rev_pm = row.get("reviews_per_month")
            reviews_per_month_filled = float(rev_pm) if rev_pm is not None and not pd.isna(rev_pm) else 0.0
        except (ValueError, TypeError):
            reviews_per_month_filled = 0.0

        try:
            avail = float(row.get("availability_365") if row.get("availability_365") is not None else 0.0)
        except (ValueError, TypeError):
            avail = 0.0
        availability_ratio = float(np.clip(avail / 365.0, 0.0, 1.0))

        try:
            host_count = float(row.get("calculated_host_listings_count") if row.get("calculated_host_listings_count") is not None else 1.0)
        except (ValueError, TypeError):
            host_count = 1.0
        host_listing_density = float(np.log1p(max(1.0, host_count)))

        try:
            latitude_raw = float(row.get("latitude") if row.get("latitude") is not None else 40.7128)
        except (ValueError, TypeError):
            latitude_raw = 40.7128

        try:
            longitude_raw = float(row.get("longitude") if row.get("longitude") is not None else -74.0060)
        except (ValueError, TypeError):
            longitude_raw = -74.0060

        room_type = str(row.get("room_type") or "Entire home/apt").strip()
        mean_p, std_p = 4.7, 0.7
        if group_stats and room_type in group_stats:
            mean_p = group_stats[room_type].get("mean", 4.7)
            std_p = group_stats[room_type].get("std", 0.7)
            if std_p <= 1e-6:
                std_p = 1.0

        price_to_type_zscore = float((price_log - mean_p) / std_p)

        name_str = row.get("name")
        text_length_name = float(len(str(name_str))) if name_str is not None and not pd.isna(name_str) else 0.0

        return {
            "price_log": price_log,
            "minimum_nights_log": minimum_nights_log,
            "number_of_reviews_log": number_of_reviews_log,
            "reviews_per_month_filled": reviews_per_month_filled,
            "availability_ratio": availability_ratio,
            "host_listing_density": host_listing_density,
            "latitude_raw": latitude_raw,
            "longitude_raw": longitude_raw,
            "price_to_type_zscore": price_to_type_zscore,
            "text_length_name": text_length_name,
            "feature_names": NON_LEAKY_FEATURE_NAMES
        }

    def generate_features(self, scores: dict, issues: list, record_age_days: float, overall_score: float) -> tuple:
        """
        Backward compatible feature extraction method for legacy rule evaluation.
        """
        missing_count = sum(1 for issue in issues if issue.get("issue_type") == "MISSING_FIELD")
        invalid_count = sum(1 for issue in issues if issue.get("issue_type") in ["INVALID_FORMAT", "INVALID_RANGE", "INVALID_VALUE"])
        consistency_count = sum(1 for issue in issues if issue.get("issue_type") == "INCONSISTENT_CROSS_FIELDS")
        duplicate_count = sum(1 for issue in issues if issue.get("issue_type") == "DUPLICATE_RECORD")

        quality_features = {
            "missing_fields": missing_count,
            "invalid_fields": invalid_count,
            "consistency_issues": consistency_count,
            "duplicate_fields": duplicate_count,
            "record_age_days": round(record_age_days, 2) if record_age_days is not None else 0.0,
        }

        # NON-LEAKY FEATURE MATRIX
        ml_ready_features = self.extract_record_features({
            "price": 100.0,
            "minimum_nights": 1.0,
            "number_of_reviews": 0.0,
            "reviews_per_month": 0.0,
            "availability_365": 100.0,
            "calculated_host_listings_count": 1.0,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "room_type": "Entire home/apt",
            "name": "Listing Sample"
        })
        return quality_features, ml_ready_features
