from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ..repositories.document_repository import DocumentRepository
from ..repositories.metadata_repository import MetadataRepository
from ..repositories.audit_repository import AuditRepository
from ..repositories.processing_repository import ProcessingRepository
from ..repositories.transaction_manager import TransactionManager
import logging
from datetime import datetime

logger = logging.getLogger('enterprise')

class PersistenceStage(BaseStage):
    """
    Persistence Stage: The ONLY stage authorized to commit pipeline results
    (metadata, OCR, standardized canonical records, audit, execution history) to DB.
    """
    def __init__(self):
        super().__init__("Persistence")
        self.doc_repo = DocumentRepository()
        self.metadata_repo = MetadataRepository()
        self.audit_repo = AuditRepository()
        self.proc_repo = ProcessingRepository()
        self.tx_manager = TransactionManager()

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.PERSISTING)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Transaction block wrapper
            def do_persist():
                # 1. Resolve OCR properties
                ocr_metadata = context.ocr_result
                ocr_conf = None
                if ocr_metadata and "confidence" in ocr_metadata:
                    ocr_conf = ocr_metadata["confidence"].get("average")

                # Copy all upload metadata from doc.metadata to context.metadata
                if not context.metadata:
                    context.metadata = {}
                if doc.metadata and isinstance(doc.metadata, dict):
                    for k, v in doc.metadata.items():
                        if k not in context.metadata or not context.metadata[k]:
                            context.metadata[k] = v

                # 2. Persist Document data fields
                self.doc_repo.save_standardized_data(
                    document_id=doc.id,
                    metadata=context.metadata,
                    standardized_record=context.standardized_record,
                    ocr_metadata=ocr_metadata,
                    ocr_confidence=ocr_conf,
                    status="COMPLETED"
                )

                # 3. Create or update ProcessingHistory entries for each stage run
                for s_name, t_info in context.timestamps["stages"].items():
                    s_status = t_info.get("status", "SUCCESS")
                    s_duration = t_info.get("duration", 0.0)
                    s_start = t_info.get("start", datetime.now())
                    s_end = t_info.get("end", datetime.now())
                    
                    self.proc_repo.create_or_update_history(
                        pipeline_id=context.pipeline_id,
                        document_id=doc.id,
                        stage_name=s_name,
                        stage_status=s_status,
                        start_time=s_start,
                        end_time=s_end,
                        duration=s_duration,
                        retry_count=context.retry_count,
                        warnings_count=len(context.warnings) if s_name == "Validation" else 0,
                        errors_count=len(context.errors) if s_status == "FAILED" else 0
                    )

                # Write Persistence stage history log manually
                self.proc_repo.create_or_update_history(
                    pipeline_id=context.pipeline_id,
                    document_id=doc.id,
                    stage_name=self.name,
                    stage_status="SUCCESS",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration=0.001,
                    retry_count=context.retry_count,
                    warnings_count=0,
                    errors_count=0
                )

                # 4. Write audit trace record
                metrics = context.metadata.get("pipeline_metrics", {}) if context.metadata else {}
                duration = metrics.get("total_pipeline_duration", 0.0)
                
                self.audit_repo.log_audit(
                    pipeline_id=context.pipeline_id,
                    document_id=doc.id,
                    user_id=context.user_info.username if context.user_info else "Anonymous",
                    start_time=context.timestamps.get("start_time"),
                    end_time=datetime.now(),
                    duration=duration,
                    status="COMPLETED",
                    warnings=context.warnings,
                    errors=context.errors
                )

                # 5. Trigger repository synchronization pipeline automatically
                from repository.services.sync_service import RepositorySynchronizationService
                sync_service = RepositorySynchronizationService()
                records_to_sync = []
                if context.standardized_record and isinstance(context.standardized_record, dict):
                    raw_records = context.standardized_record.get("standardized_record", []) or context.standardized_record.get("records", [])
                    if isinstance(raw_records, dict):
                        records_to_sync = [raw_records]
                    elif isinstance(raw_records, list):
                        records_to_sync = raw_records
                    else:
                        records_to_sync = []

                sync_res = sync_service.sync_document(
                    document_id=doc.id,
                    records=records_to_sync,
                    metadata=context.metadata or {},
                    user=context.user_info,
                    reason="Automatic repository sync from Ingestion Pipeline."
                )
                if not sync_res["success"]:
                    raise Exception(f"Repository sync stage failed: {sync_res['errors']}")

            # Invoke Database atomic transaction
            self.tx_manager.execute_atomic(do_persist)

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": {"persisted": True}
            }
        except Exception as e:
            logger.error(f"PersistenceStage execution failed for doc {doc.id if doc else 'Unknown'}: {str(e)}", exc_info=True)
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresPersistenceStage = PersistenceStage
