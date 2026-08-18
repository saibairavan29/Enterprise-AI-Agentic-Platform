import logging
from django.dispatch import receiver
from repository.signals import repository_sync_completed
from edqi.services.batch_service import BatchAssessmentService

logger = logging.getLogger(__name__)

@receiver(repository_sync_completed)
def handle_repository_sync_completed(sender, **kwargs):
    """
    Decoupled signal receiver triggered when a document repository sync commits successfully.
    Triggers batch quality assessment.
    """
    document_id = kwargs.get("document_id")
    pipeline_id = kwargs.get("pipeline_id")
    user_id = kwargs.get("user_id")

    logger.info(f"Received repository_sync_completed signal. Triggering quality assessment for Doc: {document_id}")
    
    if not document_id:
        logger.error("Signal received with missing document_id. Cannot assess quality.")
        return

    try:
        from repository.models import KnowledgeDocument
        doc = None
        
        # 1. Try resolving by UUID (direct PK)
        try:
            doc = KnowledgeDocument.objects.filter(pk=document_id).first()
        except Exception:
            pass
            
        # 2. Try resolving by source_document_id (raw ID)
        if not doc:
            try:
                doc = KnowledgeDocument.objects.filter(source_document_id=document_id).first()
            except Exception:
                pass
                
        # 3. Try converting document_id to integer (raw Document ID format)
        if not doc:
            try:
                doc_pk_int = int(document_id)
                doc = KnowledgeDocument.objects.filter(source_document_id=doc_pk_int).first()
            except Exception:
                pass
                
        if not doc:
            raise ValueError(f"KnowledgeDocument for document_id {document_id} was not found.")

        batch_service = BatchAssessmentService()
        batch_service.assess_document_records(
            document_id=doc.id,
            pipeline_id=pipeline_id,
            user_id=user_id
        )
        logger.info(f"Quality assessment completed for synchronized Document: {doc.id}")
    except Exception as e:
        logger.error(f"Error executing EDQI quality assessment from signal: {str(e)}", exc_info=True)
