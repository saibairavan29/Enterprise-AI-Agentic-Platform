import logging
from repository.services.pipeline import RepositorySynchronizationPipeline
from repository.signals import repository_sync_completed

logger = logging.getLogger(__name__)

class RepositorySynchronizationService:
    """
    Service wrapper that coordinates execution of the RepositorySynchronizationPipeline
    and dispatches decoupled event signals upon transaction commit validation.
    """
    def sync_document(self, document_id, records, metadata, user=None, reason=None) -> dict:
        """
        Executes the repository synchronization pipeline for a document.
        Emits repository_sync_completed signal if successful.
        """
        pipeline = RepositorySynchronizationPipeline()
        sync_result = pipeline.execute_sync(
            document_id=document_id,
            records=records,
            metadata=metadata,
            user=user,
            reason=reason
        )
        
        if sync_result.get("success"):
            logger.info(f"Synchronization pipeline completed successfully for document {document_id}. Emitting event signal.")
            try:
                repository_sync_completed.send(
                    sender=self.__class__,
                    document_id=str(document_id),
                    pipeline_id=sync_result.get("pipeline_id"),
                    records_count=len(records),
                    user_id=user.id if user and hasattr(user, 'id') else None
                )
            except Exception as sig_err:
                logger.error(f"Failed to dispatch repository_sync_completed signal: {str(sig_err)}", exc_info=True)
                
        return sync_result
