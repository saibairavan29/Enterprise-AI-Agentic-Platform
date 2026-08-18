import os
import json
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

class RecommendationEngine:
    """
    Decoupled dynamic engine mapping feature anomalies onto config-driven recommendations 
    defined in recommendation_rules.json.
    """
    def __init__(self):
        self.rules_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config",
            "recommendation_rules.json"
        )
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        if not os.path.exists(self.rules_path):
            ExplainabilityLogger.warning(f"recommendation_rules.json not found at {self.rules_path}. Using hardcoded default mappings.")
            return {
                "MISSING_REQUIRED_FIELD": {
                    "category": "Completeness",
                    "priority": "HIGH",
                    "priority_score": 85.0,
                    "expected_improvement": 12.0,
                    "recommendation_confidence": 95.0,
                    "recommendation": "Populate the missing mandatory field."
                },
                "INVALID_FORMAT": {
                    "category": "Validity",
                    "priority": "MEDIUM",
                    "priority_score": 65.0,
                    "expected_improvement": 7.0,
                    "recommendation_confidence": 90.0,
                    "recommendation": "Correct the value to match the expected format."
                }
            }
        try:
            with open(self.rules_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            ExplainabilityLogger.error(f"Failed to load recommendation rules: {str(e)}")
            return {}

    def generate_recommendations(self, clean_features: dict) -> list:
        """
        Scans quality indicators and returns dynamic recommendations.
        """
        ExplainabilityLogger.info("Starting quality recommendation compilation scan.")
        recommendations = []

        from edqi.rules.rules_loader import QualityRulesLoader
        rules = QualityRulesLoader.load_rules()
        weights_config = rules.get("quality_weights", {
            "completeness": 0.30,
            "validity": 0.25,
            "consistency": 0.20,
            "uniqueness": 0.15,
            "timeliness": 0.10
        })
        sum_weights = sum(weights_config.values())
        if sum_weights <= 0.0:
            sum_weights = 1.0

        # 1. Check Missing Fields
        missing_count = float(clean_features.get("missing_fields", 0.0))
        if missing_count > 0 and "MISSING_REQUIRED_FIELD" in self.rules:
            rule = self.rules["MISSING_REQUIRED_FIELD"]
            completeness_score = float(clean_features.get("completeness_score", 100.0))
            w_c = weights_config.get("completeness", 0.30) / sum_weights
            expected_improvement = round((100.0 - completeness_score) * w_c, 2)
            
            recommendations.append({
                "recommendation_type": "MISSING_REQUIRED_FIELD",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "recommendation": f"{rule['recommendation']} ({int(missing_count)} fields missing)",
                "expected_improvement": expected_improvement,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 2. Check Invalid Fields
        invalid_count = float(clean_features.get("invalid_fields", 0.0))
        if invalid_count > 0 and "INVALID_FORMAT" in self.rules:
            rule = self.rules["INVALID_FORMAT"]
            validity_score = float(clean_features.get("validity_score", 100.0))
            w_v = weights_config.get("validity", 0.25) / sum_weights
            expected_improvement = round((100.0 - validity_score) * w_v, 2)
            
            recommendations.append({
                "recommendation_type": "INVALID_FORMAT",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "recommendation": f"{rule['recommendation']} ({int(invalid_count)} values invalid)",
                "expected_improvement": expected_improvement,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 3. Check Duplicate Records
        dup_count = float(clean_features.get("duplicate_fields", 0.0))
        if dup_count > 0 and "DUPLICATE_RECORD" in self.rules:
            rule = self.rules["DUPLICATE_RECORD"]
            uniqueness_score = float(clean_features.get("uniqueness_score", 100.0))
            w_u = weights_config.get("uniqueness", 0.15) / sum_weights
            expected_improvement = round((100.0 - uniqueness_score) * w_u, 2)
            
            recommendations.append({
                "recommendation_type": "DUPLICATE_RECORD",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "recommendation": rule["recommendation"],
                "expected_improvement": expected_improvement,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 4. Check Stale Timestamp (Timeliness)
        record_age = float(clean_features.get("record_age", 0.0))
        timeliness_score = float(clean_features.get("timeliness_score", 100.0))
        if (record_age > 30 or timeliness_score < 90.0) and "STALE_RECORD" in self.rules:
            rule = self.rules["STALE_RECORD"]
            w_t = weights_config.get("timeliness", 0.10) / sum_weights
            expected_improvement = round((100.0 - timeliness_score) * w_t, 2)
            
            recommendations.append({
                "recommendation_type": "STALE_RECORD",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "recommendation": rule["recommendation"],
                "expected_improvement": expected_improvement,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # Sort recommendations by priority score descending
        recommendations = sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)
        
        ExplainabilityLogger.recommendation_generated(len(recommendations))
        return recommendations
