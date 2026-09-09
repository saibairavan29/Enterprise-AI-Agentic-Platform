import uuid
from django.db import models
from django.conf import settings

class AssistantSession(models.Model):
    """
    Tracks conversation threads for the Universal Enterprise Knowledge Assistant.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assistant_sessions'
    )
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session {self.id} - {self.title}"


class AssistantMessage(models.Model):
    """
    Stores individual query and response pairs along with 4-level explainability metadata.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        AssistantSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    content = models.TextField(help_text="Direct text answer or query.")
    
    # 4-Level Explanation Metadata
    intent_category = models.CharField(max_length=50, blank=True, default='SEMANTIC_UNSTRUCTURED')
    retrieval_method = models.CharField(max_length=50, blank=True, default='HYBRID')
    response_levels = models.JSONField(default=dict, blank=True, null=True, help_text="4-Level Progressive Response Levels")
    kg_path = models.JSONField(default=list, blank=True, null=True, help_text="Active Reasoning KG Path")
    evidence_chunks = models.JSONField(default=list, blank=True, help_text="Level 2 Evidence Chunks")
    knowledge_paths = models.JSONField(default=list, blank=True, help_text="Level 3 KG Traversal Paths")
    sources = models.JSONField(default=list, blank=True, help_text="Level 4 Source Provenance")
    
    # Execution metrics
    model_used = models.CharField(max_length=50, default='Phi-3.5-Mini-3.8B-Q4_K_M')
    latency_seconds = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message {self.id} ({self.role}) in Session {self.session_id}"

