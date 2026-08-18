import time
import logging
from datetime import datetime
from edqi.analyzers.base import BaseAnalyzer, AnalyzerResult
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class ConsistencyAnalyzer(BaseAnalyzer):
    """
    Validates cross-field rules (joining date < exit date, country-currency alignment).
    """
    def __init__(self):
        super().__init__(DataQualityDimension.CONSISTENCY.value)

    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        start_time = time.time()
        issues = []
        recommendations = []
        checks_run = 0
        violations_count = 0

        # 1. Date timeline verification: joining_date vs exit_date/termination_date
        joining_date_val = None
        exit_date_val = None
        joining_field = None
        exit_field = None

        for f in record.keys():
            f_lower = f.lower()
            if "joining" in f_lower or "start" in f_lower or "hire" in f_lower:
                joining_date_val = record.get(f)
                joining_field = f
            elif "exit" in f_lower or "termination" in f_lower or "end" in f_lower:
                exit_date_val = record.get(f)
                exit_field = f

        if joining_date_val and exit_date_val:
            checks_run += 1
            try:
                # Attempt to parse both dates
                j_date = cls_parse_date(str(joining_date_val))
                e_date = cls_parse_date(str(exit_date_val))
                if j_date and e_date and j_date > e_date:
                    violations_count += 1
                    issues.append({
                        "field_name": f"{joining_field} & {exit_field}",
                        "issue_type": "INCONSISTENT_CROSS_FIELDS",
                        "severity": "CRITICAL",
                        "expected_value": f"{joining_field} should precede {exit_field}",
                        "actual_value": f"{joining_date_val} > {exit_date_val}",
                        "description": f"Joining date '{joining_date_val}' is after exit date '{exit_date_val}'.",
                        "tags": ["Business_Rule", "Dates_Timeline"]
                    })
                    from edqi.calculators.recommendations import RecommendationEngine
                    fix, conf = RecommendationEngine.generate_recommendation("INCONSISTENT_CROSS_FIELDS", joining_field)
                    recommendations.append({
                        "field_name": f"{joining_field}/{exit_field}",
                        "suggested_fix": fix,
                        "recommendation_confidence": conf
                    })
            except Exception as e:
                pass

        # 2. Country vs Currency code alignment
        country_currency_map = rules.get("country_currency_map", {})
        if country_currency_map:
            country_val = None
            currency_val = None
            country_field = None
            currency_field = None

            for f in record.keys():
                f_lower = f.lower()
                if "country" in f_lower:
                    country_val = record.get(f)
                    country_field = f
                elif "currency" in f_lower:
                    currency_val = record.get(f)
                    currency_field = f

            if country_val and currency_val:
                checks_run += 1
                c_str = str(country_val).strip()
                curr_str = str(currency_val).strip().upper()
                
                # Check mapping if country exists in rule maps
                expected_curr = None
                for key, val in country_currency_map.items():
                    if key.lower() == c_str.lower():
                        expected_curr = val.upper()
                        break

                if expected_curr and curr_str != expected_curr:
                    violations_count += 1
                    issues.append({
                        "field_name": f"{country_field} & {currency_field}",
                        "issue_type": "INCONSISTENT_CROSS_FIELDS",
                        "severity": "MEDIUM",
                        "expected_value": f"Currency code for {c_str} should be {expected_curr}",
                        "actual_value": curr_str,
                        "description": f"Record specifies country '{c_str}' with mismatched currency code '{curr_str}' (expected '{expected_curr}').",
                        "tags": ["Business_Rule", "Reconciliation"]
                    })
                    from edqi.calculators.recommendations import RecommendationEngine
                    fix, conf = RecommendationEngine.generate_recommendation("INCONSISTENT_CROSS_FIELDS", currency_field)
                    recommendations.append({
                        "field_name": f"{country_field}/{currency_field}",
                        "suggested_fix": fix,
                        "recommendation_confidence": conf
                    })

        score = max(0.0, 100.0 - (violations_count * 25.0))

        return AnalyzerResult(
            score=round(score, 2),
            issues=issues,
            recommendations=recommendations,
            execution_time=time.time() - start_time,
            metadata={"checks_run": checks_run, "violations_count": violations_count}
        )

def cls_parse_date(date_str: str):
    """Fallback parser checking standard formats."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.split(" ")[0], fmt)
        except ValueError:
            pass
    return None
