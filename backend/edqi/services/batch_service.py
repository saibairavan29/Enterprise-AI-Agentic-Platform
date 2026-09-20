import time
import logging
import uuid
from edqi.models import EnterpriseDatasetProfile, EnterpriseQualityMetrics
from edqi.profilers.data_profiler import DataProfiler
from edqi.services.assessment_service import EnterpriseQualityAssessmentService, AssessmentContext
from edqi.builders.statistics_builder import StatisticsBuilder
from edqi.repositories.quality_repository import QualityRepository
from edqi.repositories.profile_repository import ProfileRepository
from edqi.repositories.metrics_repository import MetricsRepository
from repository.models import KnowledgeDocument, KnowledgeRecord

logger = logging.getLogger(__name__)

class BatchAssessmentService:
    """
    Service executing batch-level data quality profiling, single record assessments,
    and aggregate metrics calculations.
    """
    def __init__(self):
        self.quality_repo = QualityRepository()
        self.profile_repo = ProfileRepository()
        self.metrics_repo = MetricsRepository()
        self.profiler = DataProfiler()
        self.assessment_service = EnterpriseQualityAssessmentService()

    def assess_document_records(self, document_id: int, pipeline_id: str = None, user_id: int = None) -> EnterpriseQualityMetrics:
        """
        Orchestrates profiling and quality assessments for all records belonging to a document.
        """
        logger.info(f"Starting batch quality assessment for document {document_id}")
        start_time = time.time()
        
        batch_id = f"batch-{uuid.uuid4()}"
        if not pipeline_id:
            pipeline_id = f"pipe-{uuid.uuid4()}"

        # 1. Retrieve records and document
        doc = KnowledgeDocument.objects.filter(pk=document_id).first()
        if not doc:
            raise ValueError(f"KnowledgeDocument {document_id} was not found.")

        records = list(KnowledgeRecord.objects.filter(knowledge_document_id=document_id))
        
        # 2. Delete old profiles, reports, metrics to avoid duplicates and ensure freshness
        self.metrics_repo.delete_metrics_for_document(document_id)
        self.profile_repo.delete_profiles_for_document(document_id)
        
        record_ids = [r.id for r in records]
        if record_ids:
            self.quality_repo.delete_reports_for_records(record_ids)

        if not records:
            logger.warning(f"No records found to assess for document {document_id}")
            # Save empty metrics
            metrics = EnterpriseQualityMetrics(
                knowledge_document=doc,
                batch_id=batch_id,
                record_count=0
            )
            return self.metrics_repo.save_metrics(metrics)

        # 3. Profile records
        profiling_start = time.time()
        canonical_dicts = [r.canonical_data for r in records if r.canonical_data]
        doc_stats, field_profs = self.profiler.profile_records(canonical_dicts)
        profiling_time_ms = (time.time() - profiling_start) * 1000.0

        # Store profile
        dataset_profile = EnterpriseDatasetProfile(
            knowledge_document=doc,
            document_statistics=doc_stats,
            field_profiles=field_profs
        )
        self.profile_repo.save_profile(dataset_profile)

        # 4. Compile duplicate sets to pass down for uniqueness checks
        duplicate_employee_ids = set()
        duplicate_emails = set()

        # Find duplicate values in canonical data
        emp_ids = []
        emails = []
        for r in canonical_dicts:
            for f, val in r.items():
                if "employee_id" in f.lower() or "emp_id" in f.lower():
                    if val is not None:
                        emp_ids.append(str(val).strip())
                elif "email" in f.lower():
                    if val:
                        emails.append(str(val).strip().lower())

        # Collect duplicates (occurrences > 1)
        import collections
        duplicate_employee_ids = {k for k, v in collections.Counter(emp_ids).items() if v > 1}
        duplicate_emails = {k for k, v in collections.Counter(emails).items() if v > 1}

        # 5. Build context container
        context = AssessmentContext(
            pipeline_id=pipeline_id,
            document_id=document_id,
            batch_id=batch_id,
            user_id=user_id
        )
        # Attach sets to context dynamically
        context.duplicate_employee_ids = duplicate_employee_ids
        context.duplicate_emails = duplicate_emails
        context.profiling_time_ms = profiling_time_ms

        # 6. Run assessment loop
        reports = []
        batch_issues = []
        
        from edqi.ml_engine.services.prediction_service import PredictionService
        from edqi.explainability.explanation_service import ExplanationService
        pred_service = PredictionService()
        explain_service = ExplanationService()
        
        from django.db import connections
        for idx, rec in enumerate(records):
            if idx > 0 and idx % 10 == 0:
                connections.close_all()
                time.sleep(0.005)
            try:
                report, issues = self.assessment_service.assess_record(rec, context)
                reports.append(report)
                batch_issues.extend(issues)
                
                # Automatically compile ML Prediction and XAI SHAP Report (for top 100 records per document)
                if idx < 100:
                    try:
                        ml_feats = report.ml_ready_features
                        pred_service.predict_record_quality(rec.id, ml_feats)
                        
                        # Fetch prediction record to resolve prediction_id UUID
                        from edqi.ml_engine.models import PredictionHistory
                        pred_record = PredictionHistory.objects.filter(knowledge_record=rec).order_by('-created_at').first()
                        
                        if pred_record and pred_record.prediction_id:
                            explain_service.get_explanation_for_prediction(str(pred_record.prediction_id))
                    except Exception as ex:
                        logger.error(f"ML/XAI generation failed for record {rec.id}: {str(ex)}", exc_info=True)
                    
            except Exception as e:
                logger.error(f"Failed to assess record {rec.id}: {str(e)}", exc_info=True)

        # 7. Compile batch metrics stats
        stats = StatisticsBuilder.compile_statistics(reports, batch_issues)

        # Add execution statistics details
        execution_stats = {
            "total_duration_sec": round(time.time() - start_time, 4),
            "records_processed": len(records),
            "issues_count": len(batch_issues)
        }

        # Store metrics
        metrics = EnterpriseQualityMetrics(
            knowledge_document=doc,
            batch_id=batch_id,
            record_count=stats["record_count"],
            valid_count=stats["valid_count"],
            invalid_count=stats["invalid_count"],
            duplicate_count=stats["duplicate_count"],
            missing_count=stats["missing_count"],
            excellent_count=stats["excellent_count"],
            good_count=stats["good_count"],
            average_count=stats["average_count"],
            poor_count=stats["poor_count"],
            average_score=stats["average_score"],
            median_score=stats["median_score"],
            min_score=stats["min_score"],
            max_score=stats["max_score"],
            standard_deviation=stats["standard_deviation"],
            grade_distribution=stats["grade_distribution"],
            issue_distribution=stats["issue_distribution"],
            execution_statistics=execution_stats,
            dataset_version=f"v{doc.current_version}.0.0"
        )
        self.metrics_repo.save_metrics(metrics)

        logger.info(f"Completed batch assessment for document {document_id}. Average score: {metrics.average_score}")
        return metrics
