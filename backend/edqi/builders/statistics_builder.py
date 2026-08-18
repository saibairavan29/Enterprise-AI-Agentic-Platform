import math
import logging
import collections

logger = logging.getLogger(__name__)

class StatisticsBuilder:
    """
    Builder responsible for compiling statistical summary profiles and standard deviations.
    """
    @classmethod
    def compile_statistics(cls, reports: list, all_issues: list) -> dict:
        """
        Processes a list of reports and issues, returning an aggregated metrics dictionary.
        """
        if not reports:
            return {
                "record_count": 0, "valid_count": 0, "invalid_count": 0,
                "duplicate_count": 0, "missing_count": 0,
                "average_score": 0.0, "median_score": 0.0,
                "min_score": 0.0, "max_score": 0.0, "standard_deviation": 0.0,
                "grade_distribution": {}, "issue_distribution": {}
            }

        scores = [r.overall_quality_score for r in reports]
        scores.sort()
        
        record_count = len(reports)
        
        # Valid vs Invalid threshold (80.0 or higher is valid)
        valid_count = sum(1 for s in scores if s >= 80.0)
        invalid_count = record_count - valid_count

        # Average and Median
        average_score = sum(scores) / record_count
        
        if record_count % 2 == 1:
            median_score = scores[record_count // 2]
        else:
            median_score = (scores[record_count // 2 - 1] + scores[record_count // 2]) / 2.0

        min_score = scores[0]
        max_score = scores[-1]

        # Standard Deviation calculation
        variance = sum((s - average_score) ** 2 for s in scores) / record_count
        standard_deviation = math.sqrt(variance)

        # Grade distribution
        grades = [r.quality_grade for r in reports]
        grade_distribution = dict(collections.Counter(grades))

        # Issue distribution
        missing_count = 0
        duplicate_count = 0
        issue_types = collections.defaultdict(int)
        issue_severities = collections.defaultdict(int)
        issue_fields = collections.defaultdict(int)

        # We take raw issue dicts or objects
        for issue in all_issues:
            # issue might be a model instance or a dict
            i_type = getattr(issue, "issue_type", None) or issue.get("issue_type", "")
            severity = getattr(issue, "severity", None) or issue.get("severity", "")
            field = getattr(issue, "field_name", None) or issue.get("field_name", "")

            if i_type == "MISSING_FIELD":
                missing_count += 1
            elif i_type == "DUPLICATE_RECORD":
                duplicate_count += 1

            if i_type:
                issue_types[i_type] += 1
            if severity:
                issue_severities[severity] += 1
            if field:
                issue_fields[field] += 1

        issue_distribution = {
            "by_type": dict(issue_types),
            "by_severity": dict(issue_severities),
            "by_field": dict(issue_fields)
        }

        excellent_count = grade_distribution.get("A+", 0) + grade_distribution.get("A", 0)
        good_count = grade_distribution.get("B", 0)
        average_count = grade_distribution.get("C", 0) + grade_distribution.get("D", 0)
        poor_count = grade_distribution.get("F", 0)

        return {
            "record_count": record_count,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "duplicate_count": duplicate_count,
            "missing_count": missing_count,
            "excellent_count": excellent_count,
            "good_count": good_count,
            "average_count": average_count,
            "poor_count": poor_count,
            "average_score": round(average_score, 2),
            "median_score": round(median_score, 2),
            "min_score": round(min_score, 2),
            "max_score": round(max_score, 2),
            "standard_deviation": round(standard_deviation, 2),
            "grade_distribution": grade_distribution,
            "issue_distribution": issue_distribution
        }
