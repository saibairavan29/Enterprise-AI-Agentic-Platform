import uuid
from django.db import models
from django.conf import settings
from ingestion.models import Document

class RepositoryFolder(models.Model):
    """
    Represents a directory folder within the Enterprise Data Repository hierarchy.
    Supports nested folder structures for both Team and Personal repositories.
    """
    REPO_TYPES = [
        ('team', 'Team Repository'),
        ('personal', 'Personal Repository'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    repository_type = models.CharField(max_length=20, choices=REPO_TYPES, default='team')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='repository_folders'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    logical_path = models.CharField(max_length=1000, db_index=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = [['repository_type', 'parent', 'name']]

    def __str__(self):
        return f"{self.logical_path} ({self.repository_type})"


class KnowledgeDocument(models.Model):
    """
    Represents a unified enterprise knowledge document stored inside the repository.
    Tracks status, content versions, database statistics, and links to source files.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('DELETED', 'Deleted'),
        ('CONFLICT', 'Conflict'),
        ('PROCESSING', 'Processing'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_documents',
        help_text="References the original Phase 1 uploaded document."
    )
    folder = models.ForeignKey(
        RepositoryFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="References the logical folder containing this document."
    )
    logical_path = models.CharField(max_length=1000, blank=True, default='', db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_knowledge_documents'
    )
    title = models.CharField(max_length=255)
    current_version = models.IntegerField(default=1)
    repository_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    metadata = models.JSONField(default=dict, blank=True)
    raw_content = models.TextField(blank=True, default='')
    
    # Statistical indicators
    record_count = models.IntegerField(default=0)
    version_count = models.IntegerField(default=1)
    last_sync = models.DateTimeField(null=True, blank=True)
    last_modified = models.DateTimeField(auto_now=True)
    repository_size = models.BigIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} (v{self.current_version} - {self.repository_status})"


class KnowledgeDocumentVersion(models.Model):
    """
    Stores historical snapshots of KnowledgeDocument content, metadata, and checksums.
    """
    id = models.BigAutoField(primary_key=True)
    knowledge_document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version = models.IntegerField()
    raw_content = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=64, blank=True, default='')
    change_summary = models.JSONField(default=dict, blank=True)
    
    # Audit tracking indicators
    source_document_id = models.IntegerField(null=True, blank=True)
    reason_for_update = models.CharField(max_length=500, blank=True, default='')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repository_version_updates'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f"{self.knowledge_document.title} - Version {self.version}"


class KnowledgeRecord(models.Model):
    """
    Stores standardized tabular or entity records extracted from ingested documents.
    """
    EMBEDDING_STATUS_CHOICES = [
        ('NOT_GENERATED', 'Not Generated'),
        ('GENERATED', 'Generated'),
        ('FAILED', 'Failed'),
    ]

    id = models.BigAutoField(primary_key=True)
    knowledge_document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='records'
    )
    entity_type = models.CharField(max_length=100, blank=True, default='')
    canonical_data = models.JSONField(default=dict, blank=True)
    additional_fields = models.JSONField(default=dict, blank=True)
    
    # Vector indexing status placeholders
    embedding_status = models.CharField(
        max_length=50,
        choices=EMBEDDING_STATUS_CHOICES,
        default='NOT_GENERATED'
    )
    embedding_reference = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Record {self.id} (Doc: {self.knowledge_document_id})"


class KnowledgeRelationship(models.Model):
    """
    Stores semantic relationships between knowledge documents.
    Will be populated and consumed by future Knowledge Graph interfaces.
    """
    id = models.BigAutoField(primary_key=True)
    source_document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='source_relationships'
    )
    target_document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='target_relationships'
    )
    relationship_type = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_document.title} -[{self.relationship_type}]-> {self.target_document.title}"


class RepositoryAuditEntry(models.Model):
    """
    Security audit trails for all operations in the Enterprise Knowledge Repository.
    """
    ACTION_CHOICES = [
        ('SYNC', 'Sync'),
        ('EDIT', 'Edit'),
        ('DELETE', 'Delete'),
        ('ARCHIVE', 'Archive'),
    ]

    id = models.BigAutoField(primary_key=True)
    knowledge_document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.CharField(max_length=150, help_text="Username of the operator.")
    reason = models.TextField(blank=True, default='')
    pipeline_id = models.CharField(max_length=100, blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Repository audit entries"

    def __str__(self):
        return f"{self.user} - {self.action} on Doc {self.knowledge_document_id} at {self.timestamp}"
