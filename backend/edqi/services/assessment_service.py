import time
import logging
from edqi.models import EnterpriseDataQualityReport, DataQualityDimension
from edqi.rules.rules_loader import QualityRulesLoader
from edqi.analyzers.analyzer_registry import AnalyzerRegistry
from edqi.calculators.quality_score import QualityScoreCalculator
from edqi.calculators.quality_grade import QualityGradeCalculator
from edqi.feature_engineering.feature_generator import FeatureGenerator
from edqi.builders.report_builder import ReportBuilder
from edqi.repositories.quality_repository import QualityRepository
from repository.models import KnowledgeRecord

logger = logging.getLogger(__name__)

class AssessmentContext:
    """
    Carries tracking parameters throughout the execution of the profiling 
    and analyzer stages.
    """
    def __init__(self, pipeline_id: str, document_id: int, assessment_engine_version="1.0", 
                 feature_version="1.0", rules_version="1.0", batch_id=None, user_id=None):
        import uuid
        self.assessment_execution_id = uuid.uuid4()
        self.pipeline_id = pipeline_id
        self.document_id = document_id
        self.assessment_engine_version = assessment_engine_version
        self.feature_version = feature_version
        self.rules_version = rules_version
        self.batch_id = batch_id
        self.user_id = user_id
        self.start_time = time.time()


class EnterpriseQualityAssessmentService:
    """
    Engine orchestrating E2E data quality assessment checks on single record sets.
    """
    def __init__(self):
        self.quality_repo = QualityRepository()

    def assess_record(self, record_instance: KnowledgeRecord, context: AssessmentContext) -> tuple:
        """
        Assesses a single KnowledgeRecord.
        Returns a tuple: (report_instance, issue_instances)
        """
        logger.info(f"Assessing quality for record {record_instance.id} (Exec: {context.assessment_execution_id})")
        
        # Load rules from rules_loader
        rules = QualityRulesLoader.load_rules()
        
        canonical_data = record_instance.canonical_data or {}
        
        # Instantiate registered enabled analyzers
        analyzers = AnalyzerRegistry.get_enabled_analyzers(rules)

        dimension_scores = {}
        all_issues = []
        all_recommendations = []
        analyzer_durations = {}

        # Run dimension assessments
        assessment_start = time.time()
        for analyzer in analyzers:
            dim_start = time.time()
            res = analyzer.analyze(canonical_data, rules, context)
            dim_duration = time.time() - dim_start
            
            dimension_scores[analyzer.dimension_name] = res.score
            all_issues.extend(res.issues)
            all_recommendations.extend(res.recommendations)
            analyzer_durations[analyzer.dimension_name] = round(dim_duration, 4)
        assessment_time_ms = (time.time() - assessment_start) * 1000.0

        # Compute overall quality score & grade
        overall_score = QualityScoreCalculator.calculate_score(dimension_scores, rules)
        grade = QualityGradeCalculator.calculate_grade(overall_score, rules)

        # Retrieve previous score for trend logic
        prev_report = self.quality_repo.get_report_by_record_id(record_instance.id)
        prev_score = prev_report.overall_quality_score if prev_report else 0.0

        # Calculate record age in days for timeliness metrics
        record_age_days = 0.0
        # If timestamp exists in metadata or record, calculate age
        if record_instance.created_at:
            from django.utils import timezone
            age = timezone.now() - record_instance.created_at
            record_age_days = float(age.days)

        # Generate feature vectors (quality & ml_ready_features)
        feature_gen_start = time.time()
        feature_gen = FeatureGenerator(context.feature_version)
        quality_feats, ml_feats = feature_gen.generate_features(
            scores=dimension_scores,
            issues=all_issues,
            record_age_days=record_age_days,
            overall_score=overall_score
        )
        feature_gen_time_ms = (time.time() - feature_gen_start) * 1000.0

        # Populate execution processing trace details
        duration_ms = (time.time() - context.start_time) * 1000.0
        trace = {
            "rules_version": context.rules_version,
            "rules_snapshot": {
                "required_fields": rules.get("required_fields", []),
                "salary_min": rules.get("salary_min", 0),
                "timeliness_days": rules.get("timeliness_days", 365)
            },
            "analyzers_used": list(dimension_scores.keys()),
            "analyzer_execution_times_sec": analyzer_durations,
            "execution_time_ms": round(duration_ms, 2),
            "profiling_time_ms": round(getattr(context, "profiling_time_ms", 0.0), 2),
            "assessment_time_ms": round(assessment_time_ms, 2),
            "feature_generation_time_ms": round(feature_gen_time_ms, 2),
            "total_duration_ms": round(duration_ms, 2)
        }

        # Build models
        report = ReportBuilder.build_report_instance(
            record_id=record_instance.id,
            overall_score=overall_score,
            grade=grade,
            dim_scores=dimension_scores,
            quality_features=quality_feats,
            ml_features=ml_feats,
            trace=trace,
            context=context,
            previous_score=prev_score
        )

        # Persist report
        self.quality_repo.save_report(report)

        # Build issues associated with the saved report
        issue_instances = ReportBuilder.build_issue_instances(report, all_issues, all_recommendations)
        
        # Persist issues
        if issue_instances:
            self.quality_repo.save_issues_bulk(issue_instances)

        logger.info(f"Assessed quality score for record {record_instance.id}: {overall_score} ({grade})")
        return report, issue_instances
