import logging
from edqi.models import EnterpriseDataQualityReport, QualityIssue

logger = logging.getLogger(__name__)

class ReportBuilder:
    """
    Builder responsible for instantiating EnterpriseDataQualityReport and QualityIssue
    django model representations.
    """
    @classmethod
    def build_report_instance(cls, record_id: int, overall_score: float, grade: str, 
                              dim_scores: dict, quality_features: dict, ml_features: dict, 
                              trace: dict, context, previous_score: float = 0.0) -> EnterpriseDataQualityReport:
        """
        Creates a new EnterpriseDataQualityReport instance.
        """
        trend = "STABLE"
        if previous_score > 0.0:
            if overall_score > previous_score:
                trend = "UP"
            elif overall_score < previous_score:
                trend = "DOWN"

        # Formula description metadata
        formula_str = (
            "(0.30 * completeness) + "
            "(0.25 * validity) + "
            "(0.20 * consistency) + "
            "(0.15 * uniqueness) + "
            "(0.10 * timeliness)"
        )
        
        metadata = {
            "formula_applied": formula_str,
            "pipeline_id": context.pipeline_id,
            "document_id": str(context.document_id),
            "assessment_execution_id": str(context.assessment_execution_id),
            "batch_id": context.batch_id
        }

        report = EnterpriseDataQualityReport(
            knowledge_record_id=record_id,
            overall_quality_score=overall_score,
            previous_quality_score=previous_score,
            trend=trend,
            completeness_score=dim_scores.get("Completeness", 100.0),
            validity_score=dim_scores.get("Validity", 100.0),
            consistency_score=dim_scores.get("Consistency", 100.0),
            uniqueness_score=dim_scores.get("Uniqueness", 100.0),
            timeliness_score=dim_scores.get("Timeliness", 100.0),
            quality_grade=grade,
            assessment_status="COMPLETED",
            assessment_engine_version=context.assessment_engine_version,
            rules_version=context.rules_version,
            feature_version=context.feature_version,
            quality_features=quality_features,
            ml_ready_features=ml_features,
            processing_trace=trace,
            metadata=metadata
        )
        return report

    @classmethod
    def build_issue_instances(cls, report_instance: EnterpriseDataQualityReport, issues: list, recommendations: list) -> list:
        """
        Compiles issue representations and returns a list of QualityIssue objects.
        """
        issue_instances = []
        
        # Build lookup maps for recommendations
        rec_map = {rec.get("field_name"): rec for rec in recommendations}

        for issue in issues:
            field = issue.get("field_name")
            rec_item = rec_map.get(field, {})

            suggested_fix = rec_item.get("suggested_fix", issue.get("suggested_fix", ""))
            confidence = rec_item.get("recommendation_confidence", issue.get("recommendation_confidence", 1.0))

            issue_obj = QualityIssue(
                report=report_instance,
                field_name=field,
                issue_type=issue.get("issue_type", "GENERIC_ANOMALY"),
                severity=issue.get("severity", "MEDIUM"),
                expected_value=issue.get("expected_value", ""),
                actual_value=issue.get("actual_value", ""),
                description=issue.get("description", ""),
                suggested_fix=suggested_fix,
                recommendation_confidence=confidence,
                tags=issue.get("tags", [])
            )
            issue_instances.append(issue_obj)

        return issue_instances
