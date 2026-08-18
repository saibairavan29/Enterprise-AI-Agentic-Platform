import time
import re
import logging
from edqi.analyzers.base import BaseAnalyzer, AnalyzerResult
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class ValidityAnalyzer(BaseAnalyzer):
    """
    Evaluates format compliance (emails, phones) and numeric bounds (salaries).
    """
    def __init__(self):
        super().__init__(DataQualityDimension.VALIDITY.value)

    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        start_time = time.time()
        issues = []
        recommendations = []
        checks_run = 0
        violations_count = 0

        # 1. Email format check
        email_regex = rules.get("email_regex", "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$")
        for f in record.keys():
            if "email" in f.lower():
                val = record.get(f)
                if val:
                    checks_run += 1
                    val_str = str(val).strip()
                    if not re.match(email_regex, val_str):
                        violations_count += 1
                        issues.append({
                            "field_name": f,
                            "issue_type": "INVALID_FORMAT",
                            "severity": "HIGH",
                            "expected_value": "user@domain.com standard email layout",
                            "actual_value": val_str,
                            "description": f"Field '{f}' value '{val_str}' fails email format constraint checks.",
                            "tags": ["Formatting", "Email"]
                        })
                        from edqi.calculators.recommendations import RecommendationEngine
                        fix, conf = RecommendationEngine.generate_recommendation("INVALID_FORMAT", f)
                        recommendations.append({
                            "field_name": f,
                            "suggested_fix": fix,
                            "recommendation_confidence": conf
                        })

        # 2. Phone format check
        phone_regex = rules.get("phone_regex", "^\\+?1?\\d{9,15}$")
        for f in record.keys():
            if "phone" in f.lower():
                val = record.get(f)
                if val:
                    checks_run += 1
                    val_str = str(val).strip().replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
                    if not re.match(phone_regex, val_str):
                        violations_count += 1
                        issues.append({
                            "field_name": f,
                            "issue_type": "INVALID_FORMAT",
                            "severity": "MEDIUM",
                            "expected_value": "Standard phone digits pattern",
                            "actual_value": str(val),
                            "description": f"Field '{f}' value '{val}' fails phone format validation checks.",
                            "tags": ["Formatting", "Phone"]
                        })
                        from edqi.calculators.recommendations import RecommendationEngine
                        fix, conf = RecommendationEngine.generate_recommendation("INVALID_FORMAT", f)
                        recommendations.append({
                            "field_name": f,
                            "suggested_fix": fix,
                            "recommendation_confidence": conf
                        })

        # 3. Salary range check
        salary_min = rules.get("salary_min", 0)
        for f in record.keys():
            if "salary" in f.lower():
                val = record.get(f)
                if val is not None:
                    checks_run += 1
                    try:
                        salary_val = float(val)
                        if salary_val < salary_min:
                            violations_count += 1
                            issues.append({
                                "field_name": f,
                                "issue_type": "INVALID_RANGE",
                                "severity": "CRITICAL",
                                "expected_value": f"Salary >= {salary_min}",
                                "actual_value": str(salary_val),
                                "description": f"Field '{f}' value '{salary_val}' is less than min salary limit '{salary_min}'.",
                                "tags": ["Business_Rule", "Salary"]
                            })
                            from edqi.calculators.recommendations import RecommendationEngine
                            fix, conf = RecommendationEngine.generate_recommendation("INVALID_RANGE", f)
                            recommendations.append({
                                "field_name": f,
                                "suggested_fix": fix,
                                "recommendation_confidence": conf
                            })
                    except ValueError:
                        violations_count += 1
                        issues.append({
                            "field_name": f,
                            "issue_type": "INVALID_VALUE",
                            "severity": "HIGH",
                            "expected_value": "Numeric decimal amount",
                            "actual_value": str(val),
                            "description": f"Field '{f}' value '{val}' could not be parsed as float.",
                            "tags": ["Formatting", "Salary"]
                        })
                        from edqi.calculators.recommendations import RecommendationEngine
                        fix, conf = RecommendationEngine.generate_recommendation("INVALID_RANGE", f)
                        recommendations.append({
                            "field_name": f,
                            "suggested_fix": f"Reconcile salary field '{f}' value to represent a numeric amount.",
                            "recommendation_confidence": 0.80
                        })

        # Calculate score: each violation penalizes by 20 points
        score = max(0.0, 100.0 - (violations_count * 20.0))

        return AnalyzerResult(
            score=round(score, 2),
            issues=issues,
            recommendations=recommendations,
            execution_time=time.time() - start_time,
            metadata={"checks_run": checks_run, "violations_count": violations_count}
        )
