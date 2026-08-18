import logging
from ..pipeline.pipeline import Pipeline
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ..stages.validation_stage import ValidationStage
from ..stages.parser_stage import ParserStage
from ..stages.ocr_stage import OCRStage
from ..stages.metadata_stage import MetadataStage
from ..stages.schema_stage import SchemaStage
from ..stages.standardization_stage import StandardizationStage
from ..stages.persistence_stage import PersistenceStage
from ..response.builder import ResponseBuilder
from ..repositories.document_repository import DocumentRepository

logger = logging.getLogger('enterprise')

class IngestionOrchestrationService:
    """
    Service Layer Orchestrator. Coordinates the complete ingestion workflow from file uploads
    validations to final database persistence inside Django database transactions.
    """
    def __init__(self):
        self.doc_repo = DocumentRepository()
        self.response_builder = ResponseBuilder()

    def process_document(self, document_id, user_obj) -> dict:
        """
        Retrieves document DB records, builds contexts, runs stage collections,
        and manages failure updates outside transactional rollbacks.
        """
        logger.info(f"Ingestion pipeline orchestration started. Document ID: {document_id}")
        
        # 1. Resolve document
        doc = self.doc_repo.get_by_id(document_id)
        if not doc:
            logger.error(f"Orchestration failure: document ID {document_id} not found in repository.")
            return self.response_builder.build_response(
                success=False,
                document_id=document_id,
                pipeline_id=None,
                processing_status="FAILED",
                pipeline_duration=0.0,
                stage_execution={},
                metadata={},
                standardized_record={},
                warnings=[],
                errors=[f"Document with target ID {document_id} was not found."]
            )

        # 2. Build context
        context = PipelineContext(uploaded_document=doc, user_info=user_obj)

        # 3. Dynamic stage registration
        pipeline = Pipeline()
        pipeline.register_stage(ValidationStage())
        pipeline.register_stage(ParserStage())
        pipeline.register_stage(OCRStage())
        pipeline.register_stage(MetadataStage())
        pipeline.register_stage(SchemaStage())
        pipeline.register_stage(StandardizationStage())
        pipeline.register_stage(PersistenceStage())

        # 4. Execute sequential stages
        try:
            result = pipeline.run(context)
            
            # Persistent failure status write outside the transaction block
            if not result.success:
                self.doc_repo.update_document_status(doc.id, "FAILED")

            return result.to_dict()
        except Exception as e:
            logger.error(f"Ingestion pipeline encountered unhandled processing crash: {str(e)}", exc_info=True)
            self.doc_repo.update_document_status(doc.id, "FAILED")
            return self.response_builder.build_response(
                success=False,
                document_id=doc.id,
                pipeline_id=context.pipeline_id,
                processing_status="FAILED",
                pipeline_duration=0.0,
                stage_execution={},
                metadata={},
                standardized_record={},
                warnings=context.warnings,
                errors=context.errors or [str(e)]
            )
