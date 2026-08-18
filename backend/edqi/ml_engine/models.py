import uuid
from django.db import models

class TrainedModel(models.Model):
    """
    Persists trained ML model artifacts, evaluations, configurations, and version metadata.
    """
    STATUS_CHOICES = [
        ('TRAINING', 'Training'),
        ('VALIDATING', 'Validating'),
        ('ACTIVE', 'Active'),
        ('RETIRED', 'Retired'),
        ('FAILED', 'Failed')
    ]
    
    HEALTH_CHOICES = [
        ('HEALTHY', 'Healthy'),
        ('NEEDS_RETRAINING', 'Needs Retraining'),
        ('DEPRECATED', 'Deprecated')
    ]

    id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100, unique=True, db_index=True) # e.g. RF_v1.0.0
    version = models.CharField(max_length=50)
    algorithm = models.CharField(max_length=100) # Random Forest, XGBoost, Isolation Forest
    dataset_version = models.CharField(max_length=50)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='TRAINING')
    model_health = models.CharField(max_length=30, choices=HEALTH_CHOICES, default='HEALTHY')
    
    # Evaluation Scores
    accuracy = models.FloatField(default=0.0)
    precision = models.FloatField(default=0.0)
    recall = models.FloatField(default=0.0)
    f1_score = models.FloatField(default=0.0)
    roc_auc = models.FloatField(default=0.0)
    cross_validation_score = models.FloatField(default=0.0)
    
    # Metrics
    training_time_sec = models.FloatField(default=0.0)
    prediction_time_sec = models.FloatField(default=0.0)
    training_completed_at = models.DateTimeField(null=True, blank=True)
    last_prediction_at = models.DateTimeField(null=True, blank=True)
    prediction_count = models.IntegerField(default=0)
    
    # Reproducibility & Dimensions
    random_seed = models.IntegerField(default=42)
    training_dataset_size = models.IntegerField(default=0)
    testing_dataset_size = models.IntegerField(default=0)
    feature_count = models.IntegerField(default=0)
    
    # Large JSON Fields
    training_configuration = models.JSONField(default=dict, blank=True)
    feature_importance = models.JSONField(default=dict, blank=True)
    
    # Paths to artifacts on disk
    model_path = models.CharField(max_length=500)
    pipeline_path = models.CharField(max_length=500)
    
    supports_explainability = models.BooleanField(default=True)
    
    # Version chain & lifecycle tracking
    activated_at = models.DateTimeField(null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    parent_version = models.CharField(max_length=100, blank=True, null=True)
    next_version = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.model_name} ({self.algorithm} - {self.status})"


class PredictionHistory(models.Model):
    """
    Stores historical logs of all ML-driven quality assessments and anomaly inferences.
    """
    CONFIDENCE_LEVELS = [
        ('VERY_HIGH', 'Very High'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low')
    ]

    id = models.BigAutoField(primary_key=True)
    prediction_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    knowledge_record = models.ForeignKey(
        'repository.KnowledgeRecord',
        on_delete=models.CASCADE,
        related_name='ml_predictions',
        null=True,
        blank=True
    )
    predicted_grade = models.CharField(max_length=20) # Excellent, Good, Average, Poor
    predicted_probability = models.JSONField(default=dict, blank=True) # Full distribution classes
    
    # Anomaly Indicators
    is_anomaly = models.BooleanField(default=False)
    anomaly_score = models.FloatField(default=0.0)
    
    # Trace Versioning tags
    model_name = models.CharField(max_length=100)
    algorithm = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    dataset_version = models.CharField(max_length=50)
    feature_version = models.CharField(max_length=50, default='1.0')
    
    # Traceability & Feedback fields
    input_feature_hash = models.CharField(max_length=64, blank=True, null=True)
    feature_schema_version = models.CharField(max_length=50, default='1.0')
    pipeline_version = models.CharField(max_length=50, default='1.0')
    actual_label = models.CharField(max_length=20, blank=True, null=True)
    prediction_source = models.CharField(max_length=50, default='Rule Engine')
    
    prediction_time_ms = models.FloatField(default=0.0)
    confidence_level = models.CharField(max_length=30, choices=CONFIDENCE_LEVELS, default='MEDIUM')
    execution_trace = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prediction {self.prediction_id} -> {self.predicted_grade} (Anomaly: {self.is_anomaly})"
