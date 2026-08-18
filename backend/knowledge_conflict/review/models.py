import uuid
from django.db import models
from django.conf import settings

class ConflictReview(models.Model):
    """
    Model representing a human review decision and action resolution on a detected conflict.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RESOLVED', 'Resolved')
    ]
    DECISION_CHOICES = [
        ('CONFIRMED', 'Confirmed Conflict'),
        ('FALSE_POSITIVE', 'False Positive'),
        ('NEEDS_MORE_REVIEW', 'Needs More Review')
    ]
    RESOLUTION_CHOICES = [
        ('KEEP_SOURCE', 'Keep Source Document'),
        ('KEEP_TARGET', 'Keep Target Document'),
        ('MERGE', 'Merge Records'),
        ('MANUAL_EDIT', 'Manual Edit'),
        ('IGNORE', 'Ignore False Positive')
    ]

    id = models.BigAutoField(primary_key=True)
    review_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    conflict = models.ForeignKey(
        'knowledge_conflict.KnowledgeConflict', 
        on_delete=models.CASCADE, 
        related_name='reviews',
        help_text="Reference to the analyzed knowledge conflict."
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='reviews',
        help_text="Analyst user reviewing this conflict."
    )
    
    review_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    decision = models.CharField(max_length=50, choices=DECISION_CHOICES, null=True, blank=True)
    resolution = models.CharField(max_length=50, choices=RESOLUTION_CHOICES, null=True, blank=True)
    comments = models.TextField(blank=True, default='')
    
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review {str(self.review_id)[:8]} - Status: {self.review_status}"


class ConflictAuditHistory(models.Model):
    """
    Immutable audit logging table storing human conflict review tracking events.
    """
    ACTION_TYPES = [
        ('REVIEW_STARTED', 'Review Started'),
        ('DECISION_CONFIRMED', 'Decision Confirmed'),
        ('MERGED', 'Merged'),
        ('MANUAL_EDIT', 'Manual Edit'),
        ('IGNORE', 'Ignore'),
        ('ARCHIVED', 'Archived')
    ]

    id = models.BigAutoField(primary_key=True)
    conflict = models.ForeignKey(
        'knowledge_conflict.KnowledgeConflict',
        on_delete=models.CASCADE,
        related_name='audit_history'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=255)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, default='REVIEW_STARTED')
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    comments = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Audit {self.id} for Conflict {str(self.conflict.conflict_id)[:8]} by {self.user}"
