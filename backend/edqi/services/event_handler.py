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

        import threading
        
        def _run_async_assessment(doc_id, p_id, u_id):
            from django import db
            db.connections.close_all()
            try:
                batch_service = BatchAssessmentService()
                batch_service.assess_document_records(
                    document_id=doc_id,
                    pipeline_id=p_id,
                    user_id=u_id
                )
                logger.info(f"Quality assessment completed asynchronously for Document: {doc_id}")
            except Exception as ex:
                logger.error(f"Error executing asynchronous EDQI quality assessment: {str(ex)}", exc_info=True)
            finally:
                db.connections.close_all()

        threading.Thread(target=_run_async_assessment, args=(doc.id, pipeline_id, user_id), daemon=True).start()
        logger.info(f"Dispatched background EDQI quality assessment for Document: {doc.id}")
    except Exception as e:
        logger.error(f"Error initializing EDQI quality assessment signal: {str(e)}", exc_info=True)
