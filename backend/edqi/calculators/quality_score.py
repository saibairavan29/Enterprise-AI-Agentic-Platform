import logging
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class QualityScoreCalculator:
    """
    Computes overall data quality score using configurable weights mapping.
    """
    @classmethod
    def calculate_score(cls, dimension_scores: dict, rules: dict) -> float:
        """
        Calculates final score by multiplying each dimension score by its configured weight.
        """
        weights_config = rules.get("quality_weights", {
            "completeness": 0.30,
            "validity": 0.25,
            "consistency": 0.20,
            "uniqueness": 0.15,
            "timeliness": 0.10
        })

        # Maps dimension value to key key in rules weight config
        mapping = {
            DataQualityDimension.COMPLETENESS.value: "completeness",
            DataQualityDimension.VALIDITY.value: "validity",
            DataQualityDimension.CONSISTENCY.value: "consistency",
            DataQualityDimension.UNIQUENESS.value: "uniqueness",
            DataQualityDimension.TIMELINESS.value: "timeliness"
        }

        total_weight = 0.0
        weighted_score_sum = 0.0

        for dim_val, rule_key in mapping.items():
            w = weights_config.get(rule_key, 0.0)
            score = dimension_scores.get(dim_val, 100.0)
            
            weighted_score_sum += score * w
            total_weight += w

        if total_weight <= 0.0:
            logger.error("Sum of quality weights is 0 or negative. Defaulting score to 100.0")
            return 100.0

        # Normalize score if weights sum does not equal exactly 1.0
        final_score = weighted_score_sum / total_weight
        return round(final_score, 2)
