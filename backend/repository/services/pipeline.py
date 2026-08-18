import uuid
import logging
from django.db import transaction

from repository.services.stages.validate_stage import ValidateStage
from repository.services.stages.detection_stage import DetectionStage
from repository.services.stages.version_history_stage import VersionHistoryStage
from repository.services.stages.version_diff_stage import VersionDiffStage
from repository.services.stages.update_document_stage import UpdateDocumentStage
from repository.services.stages.update_records_stage import UpdateRecordsStage
from repository.services.stages.audit_stage import AuditStage

logger = logging.getLogger('enterprise')

class RepositorySynchronizationPipeline:
    """
    Orchestration manager that executes the repository sync stages, 
    wrapping them in an atomic database transaction context.
    """
    def __init__(self):
        self.stages = [
            ValidateStage(),
            DetectionStage(),
            VersionHistoryStage(),
            VersionDiffStage(),
            UpdateDocumentStage(),
            UpdateRecordsStage(),
            AuditStage()
        ]

    def execute_sync(self, document_id, records, metadata, user=None, reason=None) -> dict:
        """
        Runs the sequential stages inside a PostgreSQL transaction.
        Returns a pipeline execution result summary.
        """
        pipeline_id = f"repo-sync-{uuid.uuid4()}"
        context = {
            'pipeline_id': pipeline_id,
            'document_id': document_id,
            'records': records,
            'metadata': metadata,
            'user': user,
            'reason': reason
        }

        try:
            # Enforce atomic PostgreSQL transaction block
            with transaction.atomic():
                for stage in self.stages:
                    stage_name = stage.__class__.__name__
                    logger.debug(f"[Pipeline Stage] Starting {stage_name} for Doc {document_id}")
                    context = stage.execute(context)

            logger.info(f"Repository synchronization succeeded. Document ID: {document_id} | Pipeline: {pipeline_id}")
            knowledge_doc = context.get('knowledge_document')
            
            return {
                "success": True,
                "pipeline_id": pipeline_id,
                "knowledge_document_id": str(knowledge_doc.id) if knowledge_doc else None,
                "title": context.get('title'),
                "version": context.get('version', 1),
                "change_summary": context.get('change_summary', {}),
                "errors": []
            }
        except Exception as e:
            logger.error(f"Repository synchronization failed for Doc {document_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "pipeline_id": pipeline_id,
                "knowledge_document_id": None,
                "title": None,
                "version": None,
                "change_summary": {},
                "errors": [str(e)]
            }
