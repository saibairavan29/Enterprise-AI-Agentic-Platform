import time
import logging
from edqi.analyzers.base import BaseAnalyzer, AnalyzerResult
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class UniquenessAnalyzer(BaseAnalyzer):
    """
    Validates record uniqueness by cross-checking key fields (employee_id, email)
    against the batch duplicate sets.
    """
    def __init__(self):
        super().__init__(DataQualityDimension.UNIQUENESS.value)

    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        start_time = time.time()
        issues = []
        recommendations = []
        checks_run = 0
        violations_count = 0

        # Retrieve pre-computed batch duplicate sets from context metadata
        duplicate_employee_ids = getattr(context, "duplicate_employee_ids", set())
        duplicate_emails = getattr(context, "duplicate_emails", set())

        # 1. Employee ID check
        for f in record.keys():
            if "employee_id" in f.lower() or "emp_id" in f.lower():
                val = record.get(f)
                if val is not None:
                    checks_run += 1
                    val_str = str(val).strip()
                    if val_str in duplicate_employee_ids:
                        violations_count += 1
                        issues.append({
                            "field_name": f,
                            "issue_type": "DUPLICATE_RECORD",
                            "severity": "HIGH",
                            "expected_value": "Unique Employee Identifier",
                            "actual_value": val_str,
                            "description": f"Employee identifier '{val_str}' in field '{f}' is duplicated in this batch.",
                            "tags": ["Deduplication", "Employee_ID"]
                        })
                        from edqi.calculators.recommendations import RecommendationEngine
                        fix, conf = RecommendationEngine.generate_recommendation("DUPLICATE_RECORD", f)
                        recommendations.append({
                            "field_name": f,
                            "suggested_fix": fix,
                            "recommendation_confidence": conf
                        })

        # 2. Email uniqueness check
        for f in record.keys():
            if "email" in f.lower():
                val = record.get(f)
                if val:
                    checks_run += 1
                    val_str = str(val).strip().lower()
                    if val_str in duplicate_emails:
                        violations_count += 1
                        issues.append({
                            "field_name": f,
                            "issue_type": "DUPLICATE_RECORD",
                            "severity": "HIGH",
                            "expected_value": "Unique Email Address",
                            "actual_value": str(val),
                            "description": f"Email address '{val}' in field '{f}' is registered to multiple records.",
                            "tags": ["Deduplication", "Email"]
                        })
                        from edqi.calculators.recommendations import RecommendationEngine
                        fix, conf = RecommendationEngine.generate_recommendation("DUPLICATE_RECORD", f)
                        recommendations.append({
                            "field_name": f,
                            "suggested_fix": fix,
                            "recommendation_confidence": conf
                        })

        # Score calculations: duplicates reduce uniqueness to 0.0 for that specific record
        score = 100.0 if violations_count == 0 else 0.0

        return AnalyzerResult(
            score=score,
            issues=issues,
            recommendations=recommendations,
            execution_time=time.time() - start_time,
            metadata={"checks_run": checks_run, "violations_count": violations_count}
        )
