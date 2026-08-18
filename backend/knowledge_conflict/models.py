import uuid
from django.db import models

class KnowledgeCandidate(models.Model):
    """
    Model representing a generated knowledge comparison candidate pair.
    Stores metadata, text snippets, page/section references, strategy used,
    and a unique SHA-256 fingerprint hash to avoid duplication.
    """
    STATUS_CHOICES = [
        ('GENERATED', 'Generated'),
        ('QUEUED', 'Queued'),
        ('PROCESSING', 'Processing'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
        ('ARCHIVED', 'Archived')
    ]

    id = models.BigAutoField(primary_key=True)
    candidate_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    batch_id = models.CharField(max_length=100, db_index=True)
    candidate_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Traceability links
    source_document = models.ForeignKey(
        'repository.KnowledgeDocument',
        on_delete=models.CASCADE,
        related_name='source_candidates',
        help_text="Reference to the source KnowledgeDocument."
    )
    target_document = models.ForeignKey(
        'repository.KnowledgeDocument',
        on_delete=models.CASCADE,
        related_name='target_candidates',
        help_text="Reference to the comparison target KnowledgeDocument."
    )
    
    # Segment details
    source_segment_id = models.CharField(max_length=100, help_text="Unique segment identifier in source context.")
    target_segment_id = models.CharField(max_length=100, help_text="Unique segment identifier in target context.")
    source_text = models.TextField(help_text="Text content of the source segment.")
    target_text = models.TextField(help_text="Text content of the target segment.")
    source_page = models.IntegerField(null=True, blank=True, help_text="Page number in source document.")
    target_page = models.IntegerField(null=True, blank=True, help_text="Page number in target document.")
    source_section = models.CharField(max_length=255, null=True, blank=True, help_text="Section heading in source.")
    target_section = models.CharField(max_length=255, null=True, blank=True, help_text="Section heading in target.")
    
    # Matching rules details
    strategy_used = models.CharField(max_length=100, help_text="Strategy strategy name used to generate this pair.")
    strategy_confidence = models.FloatField(help_text="Configured confidence score for the strategy matching.")
    entity_type = models.CharField(max_length=100, blank=True, default='', help_text="Record entity category type (if applicable).")
    
    status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='GENERATED',
        help_text="Processing state status of this candidate."
    )
    metadata = models.JSONField(default=dict, blank=True, help_text="Dynamic matching metadata attributes.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Candidate {str(self.candidate_id)[:8]} ({self.strategy_used} - {self.status})"
 
class KnowledgeConflict(models.Model):
    """
    Model representing a semantic knowledge conflict detected between comparison candidates.
    Contains decision metrics, traceability logs, status indicators, and evidence details.
    """
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('PROCESSING', 'Processing'),
        ('REVIEW_PENDING', 'Review Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
        ('ARCHIVED', 'Archived')
    ]
    CONFLICT_TYPE_CHOICES = [
        ('CONSISTENT', 'Consistent'),
        ('DUPLICATE', 'Duplicate'),
        ('CONFLICTING', 'Conflicting'),
        ('OUTDATED', 'Outdated'),
        ('UNKNOWN', 'Unknown')
    ]
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical')
    ]

    id = models.BigAutoField(primary_key=True)
    conflict_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    knowledge_candidate = models.ForeignKey(
        'knowledge_conflict.KnowledgeCandidate', 
        on_delete=models.CASCADE, 
        related_name='conflicts',
        help_text="Reference to the comparison candidate pair."
    )
    
    # Traceability links
    source_document = models.ForeignKey(
        'repository.KnowledgeDocument', 
        on_delete=models.CASCADE, 
        related_name='source_conflicts',
        help_text="Reference to the source KnowledgeDocument."
    )
    target_document = models.ForeignKey(
        'repository.KnowledgeDocument', 
        on_delete=models.CASCADE, 
        related_name='target_conflicts',
        help_text="Reference to the target KnowledgeDocument."
    )
    
    conflict_type = models.CharField(max_length=50, choices=CONFLICT_TYPE_CHOICES, default='UNKNOWN')
    severity = models.CharField(max_length=50, choices=SEVERITY_CHOICES, default='LOW')
    
    # Similarity Metrics
    overall_similarity = models.FloatField(help_text="The primary decision similarity score.")
    similarity_metrics = models.JSONField(default=dict, blank=True, help_text="Carries cosine, length, and keyword similarity parameters.")
    confidence_score = models.FloatField()
    
    # Logic details
    embedding_model = models.CharField(max_length=100)
    embedding_metadata = models.JSONField(default=dict, blank=True, help_text="Dimensions and parameters.")
    classifier_used = models.CharField(max_length=100)
    explanation = models.TextField(blank=True, default='')
    evidence = models.JSONField(default=dict, blank=True, help_text="Specific overlapping fields or mismatch indicators.")
    
    # Execution Tracking
    processing_trace = models.JSONField(default=dict, help_text="System-level execution details for auditing.")
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='NEW')
    metadata = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conflict {str(self.conflict_id)[:8]} ({self.conflict_type} - {self.severity})"

# Import review and audit history models for migration registration
from .review.models import ConflictReview, ConflictAuditHistory


