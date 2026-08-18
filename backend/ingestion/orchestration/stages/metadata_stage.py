from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ingestion.metadata.services.metadata_service import MetadataOrchestrationService

class MetadataStage(BaseStage):
    """
    Metadata Stage: Extracts structural, content, source, and analytics statistics metadata.
    """
    def __init__(self):
        super().__init__("Metadata")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.METADATA_EXTRACTED)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Gather previous stages intermediate data
            parser_res = context.parser_result or {}
            ocr_res = context.ocr_result

            # Invoke Milestone 5 Metadata service
            metadata_service = MetadataOrchestrationService()
            metadata_obj = metadata_service.extract(doc, parser_res, ocr_res)

            context.metadata = metadata_obj

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": metadata_obj
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresMetadataStage = MetadataStage
