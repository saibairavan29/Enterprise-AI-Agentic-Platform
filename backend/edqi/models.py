import uuid
from django.db import models
from enum import Enum

class DataQualityDimension(Enum):
    COMPLETENESS = "Completeness"
    VALIDITY = "Validity"
    CONSISTENCY = "Consistency"
    UNIQUENESS = "Uniqueness"
    TIMELINESS = "Timeliness"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]


class EnterpriseDataQualityReport(models.Model):
    """
    Persists rule assessment scores, features, and logs for a single KnowledgeRecord.
    """
    id = models.BigAutoField(primary_key=True)
    report_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    knowledge_record = models.ForeignKey(
        'repository.KnowledgeRecord',
        on_delete=models.CASCADE,
        related_name='quality_reports'
    )
    overall_quality_score = models.FloatField()
    previous_quality_score = models.FloatField(default=0.0)
    trend = models.CharField(max_length=20, default='STABLE') # UP, DOWN, STABLE
    
    # Dimension Scores
    completeness_score = models.FloatField()
    validity_score = models.FloatField()
    consistency_score = models.FloatField()
    uniqueness_score = models.FloatField()
    timeliness_score = models.FloatField()
    
    quality_grade = models.CharField(max_length=5)
    assessment_status = models.CharField(max_length=50, default='PENDING') # PENDING, RUNNING, COMPLETED, FAILED, VERIFIED
    
    # Versioning
    assessment_engine_version = models.CharField(max_length=20, default='1.0')
    rules_version = models.CharField(max_length=20, default='1.0')
    feature_version = models.CharField(max_length=20, default='1.0')
    
    # Feature Vectors
    quality_features = models.JSONField(default=dict, blank=True)
    ml_ready_features = models.JSONField(default=dict, blank=True)
    
    # Trace & Metadata
    processing_trace = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report {self.report_id} - Score: {self.overall_quality_score} ({self.quality_grade})"


class QualityIssue(models.Model):
    """
    Stores distinct data quality anomalies identified on a record.
    """
    id = models.BigAutoField(primary_key=True)
    issue_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    report = models.ForeignKey(
        EnterpriseDataQualityReport,
        on_delete=models.CASCADE,
        related_name='issues'
    )
    field_name = models.CharField(max_length=255)
    issue_type = models.CharField(max_length=100) # e.g. MISSING_FIELD, INVALID_EMAIL, OUTDATED_TIMESTAMP
    severity = models.CharField(max_length=50, default='MEDIUM') # INFO, LOW, MEDIUM, HIGH, CRITICAL
    
    expected_value = models.CharField(max_length=255, null=True, blank=True)
    actual_value = models.CharField(max_length=255, null=True, blank=True)
    
    description = models.TextField()
    suggested_fix = models.TextField(blank=True, default='')
    recommendation_confidence = models.FloatField(default=1.0)
    tags = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Issue {self.issue_id} on {self.field_name} - {self.severity}"


class EnterpriseDatasetProfile(models.Model):
    """
    Stores summary metadata characteristics of the columns in a KnowledgeDocument.
    """
    id = models.BigAutoField(primary_key=True)
    profile_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    knowledge_document = models.ForeignKey(
        'repository.KnowledgeDocument',
        on_delete=models.CASCADE,
        related_name='dataset_profiles'
    )
    document_statistics = models.JSONField(default=dict, blank=True) # total_records, total_fields, null_percentage, duplicate_percentage
    field_profiles = models.JSONField(default=dict, blank=True) # field-level details: datatype, null %, unique %, min, max, avg length, top values
    
    # Lineage fields
    source_name = models.CharField(max_length=200, default='Local Ingestion')
    source_type = models.CharField(max_length=50, default='File')
    source_path = models.TextField(blank=True, default='')
    ingestion_batch_id = models.CharField(max_length=100, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile {self.profile_id} for Document {self.knowledge_document_id}"


class EnterpriseQualityMetrics(models.Model):
    """
    Stores statistical aggregates calculated at the batch/document level.
    """
    id = models.BigAutoField(primary_key=True)
    metrics_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    knowledge_document = models.ForeignKey(
        'repository.KnowledgeDocument',
        on_delete=models.CASCADE,
        related_name='quality_metrics'
    )
    batch_id = models.CharField(max_length=255)
    
    # Aggregates
    record_count = models.IntegerField(default=0)
    valid_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    missing_count = models.IntegerField(default=0)
    
    # Grade Counts
    excellent_count = models.IntegerField(default=0)
    good_count = models.IntegerField(default=0)
    average_count = models.IntegerField(default=0)
    poor_count = models.IntegerField(default=0)
    
    # Scores
    average_score = models.FloatField(default=0.0)
    median_score = models.FloatField(default=0.0)
    min_score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=0.0)
    standard_deviation = models.FloatField(default=0.0)
    
    # Distributions
    grade_distribution = models.JSONField(default=dict, blank=True)
    issue_distribution = models.JSONField(default=dict, blank=True)
    execution_statistics = models.JSONField(default=dict, blank=True)
    
    dataset_version = models.CharField(max_length=50, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Metrics {self.metrics_id} - Batch {self.batch_id}"

# Register ML Engine models
from edqi.ml_engine.models import TrainedModel, PredictionHistory

# Register Explainability models
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
