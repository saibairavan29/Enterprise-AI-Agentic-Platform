from django.db import models

class CoreModel(models.Model):
    """
    Abstract base model containing fields used in almost all tables.
    Tracks creation, modification dates, and operational status.
    """
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the record was last updated.")
    status = models.CharField(
        max_length=50, 
        default='active', 
        help_text="State of the record (e.g., active, processed, completed, failed)."
    )

    class Meta:
        abstract = True
