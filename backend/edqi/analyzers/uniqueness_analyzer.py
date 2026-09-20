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

        # 1. Unique Key / ID checks (dynamically check any identifier or key field)
        duplicate_keys = getattr(context, "duplicate_keys", {})
        if not duplicate_keys and hasattr(context, "duplicate_employee_ids"):
            duplicate_keys = {"id": getattr(context, "duplicate_employee_ids", set()), "email": getattr(context, "duplicate_emails", set())}

        for f, val in record.items():
            if val is None:
                continue
            val_str = str(val).strip()
            f_lower = f.lower()

            GENERIC_NON_IDS = {'yes', 'no', 'true', 'false', 'y', 'n', '0', '1', 'null', 'none', 'n/a', 'nan', ''}
            if val_str.lower() in GENERIC_NON_IDS:
                continue

            # Check if this field name is a valid unique ID column
            is_prose = any(prose in f_lower for prose in ['requirement', 'metric', 'indicator', 'performance', 'finding', 'description', 'notes', 'comment', 'question', 'criteria', 'task', 'scope', 'action', 'result', 'status'])
            is_id_field = not is_prose and (
                f_lower in ['id', 'code', 'key', 'uuid', 'record_id', 'employee_id', 'project_id', 'incident_id', 'order_id', 'doc_id', 'ref', 'reference', 'serial_no', 'account_no'] or
                f_lower.endswith("_id") or f_lower.endswith("_code") or f_lower.endswith("_num") or f_lower.endswith("_number") or f_lower.endswith("_ref") or f_lower.endswith("_key") or
                f_lower.startswith("id_") or f_lower.startswith("code_") or f_lower.startswith("key_") or "email" in f_lower
            )
            if is_id_field:
                checks_run += 1
                # Check against batch duplicate sets
                dup_set = duplicate_keys.get(f, set())
                if not dup_set:
                    # check fallback keys
                    for k_key, k_set in duplicate_keys.items():
                        if k_key in f_lower or f_lower in k_key:
                            dup_set = k_set
                            break
                if val_str in dup_set:
                    violations_count += 1
                    issues.append({
                        "field_name": f,
                        "issue_type": "DUPLICATE_RECORD",
                        "severity": "HIGH",
                        "expected_value": f"Unique Value for {f}",
                        "actual_value": val_str,
                        "description": f"Identifier value '{val_str}' in field '{f}' is duplicated across records.",
                        "tags": ["Deduplication", f]
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
