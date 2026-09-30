from django.db import models
from django.conf import settings
from core.models import CoreModel
from common.constants import PROCESS_STATUS, VALIDATION_STATUS
from common.parser_types import ParserType

class Document(CoreModel):
    """
    Model representing an uploaded enterprise file. Tracks metadata, parsing state,
    and references the active system operator who uploaded the document.
    """
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="The system user who uploaded this document."
    )
    file = models.FileField(
        upload_to='raw/', 
        help_text="Path to the stored file inside the Uploads/raw/ directory."
    )
    file_hash = models.CharField(
        max_length=64, 
        unique=True, 
        help_text="SHA-256 hash of the file contents to enforce deduplication."
    )
    original_name = models.CharField(
        max_length=255, 
        help_text="The original filename before upload storage saving."
    )
    file_size = models.BigIntegerField(
        help_text="The physical file size in bytes."
    )
    mime_type = models.CharField(
        max_length=100, 
        help_text="The verified MIME content-type of the file."
    )
    parser_type = models.CharField(
        max_length=20,
        choices=[(tag.value, tag.name) for tag in ParserType],
        default=ParserType.TEXT.value,
        help_text="The classification type indicating which parsing strategy to execute."
    )
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESS_STATUS, 
        default='UPLOADED',
        help_text="Parsing processing status of this document."
    )
    validation_status = models.CharField(
        max_length=20, 
        choices=VALIDATION_STATUS, 
        default='pending',
        help_text="Data Quality validation state classified by EDQI."
    )
    metadata = models.JSONField(
        null=True, 
        blank=True,
        help_text="Parsed/extracted structural header metadata."
    )
    standardized_record = models.JSONField(
        null=True, 
        blank=True,
        help_text="Standardized enterprise schema mapping dictionary."
    )
    ocr_confidence = models.FloatField(
        null=True, 
        blank=True,
        help_text="Average word-level confidence percentage returned by the OCR Engine."
    )
    ocr_metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="Persistent OCR execution metadata including confidence metrics and timestamps."
    )

    def __str__(self):
        return f"{self.original_name} ({self.file_hash[:8]})"

class ProcessingHistory(models.Model):
    """
    Model representing execution details of individual ingestion pipeline runs.
    """
    pipeline_id = models.CharField(
        max_length=50,
        help_text="Unique pipeline execution correlation identifier."
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='processing_histories',
        help_text="The target document processed in this pipeline run."
    )
    stage_name = models.CharField(
        max_length=50,
        help_text="Name of the execution stage."
    )
    stage_status = models.CharField(
        max_length=20,
        help_text="Completion status of the stage (e.g. SUCCESS, FAILED, SKIPPED)."
    )
    start_time = models.DateTimeField(
        help_text="Execution start timestamp of this stage."
    )
    end_time = models.DateTimeField(
        help_text="Execution end timestamp of this stage."
    )
    execution_duration = models.FloatField(
        help_text="Execution time in seconds."
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retries attempted."
    )
    warning_count = models.IntegerField(
        default=0,
        help_text="Number of warnings compiled."
    )
    error_count = models.IntegerField(
        default=0,
        help_text="Number of errors compiled."
    )

    def __str__(self):
        return f"{self.pipeline_id} - {self.stage_name} ({self.stage_status})"


class ProcessedEmail(models.Model):
    """
    Persistent record tracking Gmail IMAP enterprise emails processed by the platform.
    Ensures idempotent Celery Beat polling and prevents duplicate ingestion of identical email messages.
    """
    message_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique Gmail Message-ID header or IMAP UID identifier."
    )
    sender = models.CharField(
        max_length=255,
        help_text="Sender email address."
    )
    recipient = models.CharField(
        max_length=255,
        help_text="Recipient enterprise mailbox address."
    )
    subject = models.CharField(
        max_length=500,
        blank=True,
        help_text="Email subject line."
    )
    received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Email received timestamp."
    )
    body = models.TextField(
        blank=True,
        help_text="Extracted email body content."
    )
    has_attachments = models.BooleanField(
        default=False,
        help_text="Flag indicating if the email contained file attachments."
    )
    attachment_count = models.IntegerField(
        default=0,
        help_text="Number of file attachments extracted from the email."
    )
    attachment_names = models.JSONField(
        default=list,
        blank=True,
        help_text="List of attachment filenames extracted."
    )
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the email was processed by the Celery worker."
    )
    status = models.CharField(
        max_length=20,
        default='SUCCESS',
        help_text="Processing status (SUCCESS, FAILED, DUPLICATE_SKIPPED)."
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if email processing encountered an exception."
    )
    documents = models.ManyToManyField(
        Document,
        blank=True,
        related_name='source_emails',
        help_text="Documents created and ingested from this email message (body or attachments)."
    )

    def __str__(self):
        return f"Email {self.message_id[:30]} from {self.sender} ({self.status})"

