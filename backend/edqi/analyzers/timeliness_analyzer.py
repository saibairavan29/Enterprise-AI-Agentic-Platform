import time
import logging
from datetime import datetime, timezone
from edqi.analyzers.base import BaseAnalyzer, AnalyzerResult
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class TimelinessAnalyzer(BaseAnalyzer):
    """
    Evaluates data freshness based on last_updated fields relative to thresholds.
    """
    def __init__(self):
        super().__init__(DataQualityDimension.TIMELINESS.value)

    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        start_time = time.time()
        issues = []
        recommendations = []
        checks_run = 0
        violations_count = 0

        # Try to find a date field in the record
        record_date = None
        date_field = None
        for f in record.keys():
            f_lower = f.lower()
            if ("updated" in f_lower or "modified" in f_lower or "timestamp" in f_lower or "review" in f_lower) and "dob" not in f_lower and "hire" not in f_lower and "birth" not in f_lower:
                val = record.get(f)
                if val:
                    try:
                        from edqi.analyzers.consistency_analyzer import cls_parse_date
                        parsed = cls_parse_date(str(val))
                        if parsed:
                            record_date = parsed
                            date_field = f
                            break
                    except Exception:
                        pass

        # If no audit/update field is found in record, default to today
        if not record_date:
            record_date = datetime.now()
            date_field = "Current Time (Fallback)"

        checks_run += 1
        now = datetime.now()
        age = now - record_date
        age_days = max(0.0, float(age.days))
        
        timeliness_days = rules.get("timeliness_days", 365)
        
        if age_days > timeliness_days:
            violations_count += 1
            issues.append({
                "field_name": date_field,
                "issue_type": "OUTDATED_RECORD",
                "severity": "LOW",
                "expected_value": f"Record age <= {timeliness_days} days",
                "actual_value": f"{int(age_days)} days",
                "description": f"Record has not been updated for {int(age_days)} days, exceeding the timeliness limit of {timeliness_days} days.",
                "tags": ["Freshness", "Outdated"]
            })
            from edqi.calculators.recommendations import RecommendationEngine
            fix, conf = RecommendationEngine.generate_recommendation("OUTDATED_RECORD", date_field)
            recommendations.append({
                "field_name": date_field,
                "suggested_fix": fix,
                "recommendation_confidence": conf
            })

            # Score decay penalty
            excess_pct = (age_days - timeliness_days) / timeliness_days * 100.0
            score = max(0.0, 100.0 - excess_pct)
        else:
            score = 100.0

        return AnalyzerResult(
            score=round(score, 2),
            issues=issues,
            recommendations=recommendations,
            execution_time=time.time() - start_time,
            metadata={"record_age_days": age_days, "threshold_days": timeliness_days, "checks_run": checks_run}
        )
