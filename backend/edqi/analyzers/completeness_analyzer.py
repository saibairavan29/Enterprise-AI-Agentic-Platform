import time
import logging
from edqi.analyzers.base import BaseAnalyzer, AnalyzerResult
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class CompletenessAnalyzer(BaseAnalyzer):
    """
    Analyzes whether required fields are populated in the record.
    """
    def __init__(self):
        super().__init__(DataQualityDimension.COMPLETENESS.value)

    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        start_time = time.time()
        required_fields = rules.get("required_fields", [])
        
        if not required_fields:
            return AnalyzerResult(score=100.0, execution_time=time.time() - start_time)

        missing_count = 0
        issues = []
        recommendations = []

        FIELD_ALIASES = {
            "employee_id": ["empid", "emp_id", "employee_id", "id", "employeeid", "employee_name"],
            "department": ["department", "dept", "deptid"],
            "salary": ["salary", "pay", "annual_salary"],
            "joining_date": ["dateofhire", "joining_date", "hire_date", "date_of_hire", "doj", "lastperformancereview_date"],
            "email": ["email", "email_address", "work_email"]
        }
        
        # Build lower map of record
        rec_lower = {str(k).lower().replace("_", "").replace(" ", ""): v for k, v in record.items()}

        for f in required_fields:
            clean_f = str(f).lower().replace("_", "").replace(" ", "")
            aliases = FIELD_ALIASES.get(clean_f, [clean_f])
            
            val = None
            found_field = False
            for alias in aliases:
                if alias in rec_lower:
                    found_field = True
                    candidate = rec_lower[alias]
                    if candidate is not None and str(candidate).strip() != "" and str(candidate).strip().lower() != "null":
                        val = candidate
                        break
            
            # Check for null representation or empty strings
            if val is None and found_field:
                missing_count += 1
                
                issue = {
                    "field_name": f,
                    "issue_type": "MISSING_FIELD",
                    "severity": "HIGH",
                    "expected_value": "Non-null value matching schema",
                    "actual_value": "NULL / Empty",
                    "description": f"Required field '{f}' is missing or empty in record.",
                    "tags": ["Missing Data", f"Field_{f}"]
                }
                issues.append(issue)

                from edqi.calculators.recommendations import RecommendationEngine
                fix, conf = RecommendationEngine.generate_recommendation("MISSING_FIELD", f)
                recommendations.append({
                    "field_name": f,
                    "suggested_fix": fix,
                    "recommendation_confidence": conf
                })

        score = max(0.0, 100.0 - (missing_count / len(required_fields) * 100.0))

        return AnalyzerResult(
            score=round(score, 2),
            issues=issues,
            recommendations=recommendations,
            execution_time=time.time() - start_time,
            metadata={"total_required_fields": len(required_fields), "missing_fields_count": missing_count}
        )
