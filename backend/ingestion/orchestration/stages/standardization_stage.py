from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ingestion.standardization.services.standardization_service import EnterpriseDataStandardizationService

class StandardizationStage(BaseStage):
    """
    Standardization Stage: Converts canonical mapping structures into formatted cleaned elements.
    """
    def __init__(self):
        super().__init__("Standardization")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.STANDARDIZED)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Standardize records
            canonical_records = context.canonical_record or {}
            
            # Carry metadata inline
            if "metadata" not in canonical_records and context.metadata:
                canonical_records["metadata"] = context.metadata

            standardizer = EnterpriseDataStandardizationService()
            standardized_obj = standardizer.standardize(canonical_records)

            context.standardized_record = standardized_obj

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": standardized_obj
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresStandardizationStage = StandardizationStage
