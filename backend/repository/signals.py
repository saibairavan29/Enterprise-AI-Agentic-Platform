import django.dispatch

# Signal emitted when repository synchronization has completed successfully.
# Providing: sender, document_id (str), pipeline_id (str), records_count (int), user_id (optional, int)
repository_sync_completed = django.dispatch.Signal()
