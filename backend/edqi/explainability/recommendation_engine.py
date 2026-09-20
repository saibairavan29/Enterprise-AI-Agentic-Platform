import os
import json
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

class RecommendationEngine:
    """
    Decoupled dynamic engine mapping feature anomalies onto config-driven recommendations 
    defined in recommendation_rules.json with explicit file, record ID, and target field provenance.
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
            ExplainabilityLogger.warning(f"recommendation_rules.json not found at {self.rules_path}. Using default mappings.")
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

    def generate_recommendations(self, clean_features: dict, canonical_data: dict = None, source_file: str = "Dataset File", record_label: str = "") -> list:
        """
        Scans quality indicators and returns dynamic recommendations with file and record provenance.
        """
        ExplainabilityLogger.info("Starting quality recommendation compilation scan.")
        recommendations = []
        cdata = canonical_data or {}
        file_name = source_file or "Ingested Dataset File"
        rec_label = record_label or (f"Record {cdata.get('id')}" if cdata.get('id') else "Target Record")

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

        from edqi.calculators.quality_score import QualityScoreCalculator

        # Check Specific Field Violations generically in canonical_data
        # 1. Numeric negative bound check for numeric fields
        for k, val in cdata.items():
            if val is not None and isinstance(val, (int, float, str)):
                try:
                    num_val = float(str(val).replace('$', '').replace(',', '').strip())
                    if num_val < 0 and ("price" in k.lower() or "cost" in k.lower() or "amount" in k.lower() or "val" in k.lower() or "num" in k.lower() or "score" in k.lower()):
                        impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Validity", dim_delta_single=5.0, issue_count=1, file_category="tabular", rules=rules)
                        recommendations.append({
                            "recommendation_type": "INVALID_NUMERIC_RANGE",
                            "category": "Validity",
                            "priority": "HIGH",
                            "priority_score": 90.0,
                            "field_name": k,
                            "current_value": str(val),
                            "source_file": file_name,
                            "record_label": rec_label,
                            "recommendation": f"Correct negative numeric value ({num_val}) in file '{file_name}' for {rec_label} (Target Field: {k}).",
                            "expected_improvement": impact["overall_score_impact"],
                            "affected_dimension": impact["affected_dimension"],
                            "current_dimension_score": impact["current_dimension_score"],
                            "projected_dimension_score": impact["projected_dimension_score"],
                            "dimension_improvement": impact["dimension_improvement"],
                            "dimension_weight": impact["dimension_weight"],
                            "overall_score_impact": impact["overall_score_impact"],
                            "current_overall_score": impact["current_overall_score"],
                            "projected_overall_score": impact["projected_overall_score"],
                            "quantifiable": True,
                            "recommendation_confidence": 98.0
                        })
                except Exception:
                    pass

        # 2. Email format check
        for k, val in cdata.items():
            if "email" in k.lower() and val:
                email_str = str(val).strip()
                if '@' not in email_str or '.' not in email_str or '_invalid' in email_str:
                    impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Validity", dim_delta_single=5.0, issue_count=1, file_category="tabular", rules=rules)
                    recommendations.append({
                        "recommendation_type": "INVALID_EMAIL_FORMAT",
                        "category": "Validity",
                        "priority": "HIGH",
                        "priority_score": 88.0,
                        "field_name": k,
                        "current_value": email_str,
                        "source_file": file_name,
                        "record_label": rec_label,
                        "recommendation": f"Fix invalid email format '{email_str}' in file '{file_name}' for {rec_label} (Target Field: {k}).",
                        "expected_improvement": impact["overall_score_impact"],
                        "affected_dimension": impact["affected_dimension"],
                        "current_dimension_score": impact["current_dimension_score"],
                        "projected_dimension_score": impact["projected_dimension_score"],
                        "dimension_improvement": impact["dimension_improvement"],
                        "dimension_weight": impact["dimension_weight"],
                        "overall_score_impact": impact["overall_score_impact"],
                        "current_overall_score": impact["current_overall_score"],
                        "projected_overall_score": impact["projected_overall_score"],
                        "quantifiable": True,
                        "recommendation_confidence": 95.0
                    })

        # 3. Missing Fields check
        missing_count = float(clean_features.get("missing_fields", 0.0))
        if missing_count > 0 and "MISSING_REQUIRED_FIELD" in self.rules:
            rule = self.rules["MISSING_REQUIRED_FIELD"]
            completeness_score = float(clean_features.get("completeness_score", 100.0))
            dim_delta = 100.0 - completeness_score
            impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Completeness", dim_delta_single=dim_delta, issue_count=1, file_category="tabular", rules=rules)
            
            missing_fields_list = [k for k, v in cdata.items() if v is None or str(v).strip() in ['', 'N/A', 'null', 'None']]
            missing_str = ", ".join(missing_fields_list) if missing_fields_list else f"{int(missing_count)} fields"

            recommendations.append({
                "recommendation_type": "MISSING_REQUIRED_FIELD",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "field_name": missing_str,
                "current_value": "NULL / Empty",
                "source_file": file_name,
                "record_label": rec_label,
                "recommendation": f"Populate missing required field(s) '{missing_str}' in file '{file_name}' for {rec_label}.",
                "expected_improvement": impact["overall_score_impact"],
                "affected_dimension": impact["affected_dimension"],
                "current_dimension_score": impact["current_dimension_score"],
                "projected_dimension_score": impact["projected_dimension_score"],
                "dimension_improvement": impact["dimension_improvement"],
                "dimension_weight": impact["dimension_weight"],
                "overall_score_impact": impact["overall_score_impact"],
                "current_overall_score": impact["current_overall_score"],
                "projected_overall_score": impact["projected_overall_score"],
                "quantifiable": True,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 4. Check Invalid Fields aggregate
        invalid_count = float(clean_features.get("invalid_fields", 0.0))
        if invalid_count > 0 and not recommendations and "INVALID_FORMAT" in self.rules:
            rule = self.rules["INVALID_FORMAT"]
            validity_score = float(clean_features.get("validity_score", 100.0))
            dim_delta = 100.0 - validity_score
            impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Validity", dim_delta_single=dim_delta, issue_count=1, file_category="tabular", rules=rules)
            
            recommendations.append({
                "recommendation_type": "INVALID_FORMAT",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "field_name": "Multiple Fields",
                "current_value": "Invalid Format",
                "source_file": file_name,
                "record_label": rec_label,
                "recommendation": f"Correct {int(invalid_count)} invalid attribute values in file '{file_name}' for {rec_label}.",
                "expected_improvement": impact["overall_score_impact"],
                "affected_dimension": impact["affected_dimension"],
                "current_dimension_score": impact["current_dimension_score"],
                "projected_dimension_score": impact["projected_dimension_score"],
                "dimension_improvement": impact["dimension_improvement"],
                "dimension_weight": impact["dimension_weight"],
                "overall_score_impact": impact["overall_score_impact"],
                "current_overall_score": impact["current_overall_score"],
                "projected_overall_score": impact["projected_overall_score"],
                "quantifiable": True,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 5. Check Duplicate Records
        dup_count = float(clean_features.get("duplicate_fields", 0.0))
        if dup_count > 0 and "DUPLICATE_RECORD" in self.rules:
            rule = self.rules["DUPLICATE_RECORD"]
            uniqueness_score = float(clean_features.get("uniqueness_score", 100.0))
            dim_delta = 100.0 - uniqueness_score
            impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Uniqueness", dim_delta_single=dim_delta, issue_count=1, file_category="tabular", rules=rules)
            
            recommendations.append({
                "recommendation_type": "DUPLICATE_RECORD",
                "category": "Data Uniqueness",
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "field_name": "Identifier / Key Fields",
                "current_value": "Duplicate Entry",
                "source_file": file_name,
                "record_label": rec_label,
                "problem_what": "Potential Full-Row Duplicate Record",
                "problem_where": f"File: {file_name} → {rec_label}",
                "problem_why": "Identical content found across comparable populated fields, affecting Data Uniqueness.",
                "problem_action": f"Review whether the repeated record entry in file '{file_name}' for {rec_label} is intentional.",
                "recommendation": f"Review whether the repeated record entry in file '{file_name}' for {rec_label} is intentional.",
                "expected_improvement": impact["overall_score_impact"],
                "affected_dimension": impact["affected_dimension"],
                "current_dimension_score": impact["current_dimension_score"],
                "projected_dimension_score": impact["projected_dimension_score"],
                "dimension_improvement": impact["dimension_improvement"],
                "dimension_weight": impact["dimension_weight"],
                "overall_score_impact": impact["overall_score_impact"],
                "current_overall_score": impact["current_overall_score"],
                "projected_overall_score": impact["projected_overall_score"],
                "quantifiable": True,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # 6. Check Stale Timestamp (Timeliness)
        record_age = float(clean_features.get("record_age", 0.0))
        timeliness_score = float(clean_features.get("timeliness_score", 100.0))
        if (record_age > 30 or timeliness_score < 90.0) and "STALE_RECORD" in self.rules:
            rule = self.rules["STALE_RECORD"]
            dim_delta = 100.0 - timeliness_score
            impact = QualityScoreCalculator.calculate_repair_impact(clean_features, "Timeliness", dim_delta_single=dim_delta, issue_count=1, file_category="tabular", rules=rules)
            
            recommendations.append({
                "recommendation_type": "STALE_RECORD",
                "category": rule["category"],
                "priority": rule["priority"],
                "priority_score": rule["priority_score"],
                "field_name": "Timestamp / Date Fields",
                "current_value": f"Age: {int(record_age)} days",
                "source_file": file_name,
                "record_label": rec_label,
                "recommendation": f"Refresh outdated record attributes in file '{file_name}' for {rec_label}.",
                "expected_improvement": impact["overall_score_impact"],
                "affected_dimension": impact["affected_dimension"],
                "current_dimension_score": impact["current_dimension_score"],
                "projected_dimension_score": impact["projected_dimension_score"],
                "dimension_improvement": impact["dimension_improvement"],
                "dimension_weight": impact["dimension_weight"],
                "overall_score_impact": impact["overall_score_impact"],
                "current_overall_score": impact["current_overall_score"],
                "projected_overall_score": impact["projected_overall_score"],
                "quantifiable": True,
                "recommendation_confidence": rule["recommendation_confidence"]
            })

        # Sort recommendations by priority score descending
        recommendations = sorted(recommendations, key=lambda x: x["priority_score"], reverse=True)
        
        ExplainabilityLogger.recommendation_generated(len(recommendations))
        return recommendations
