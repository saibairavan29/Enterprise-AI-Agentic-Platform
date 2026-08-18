from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ingestion.schema.services.schema_service import EnterpriseSchemaMappingService

class SchemaStage(BaseStage):
    """
    Schema Mapping Stage: Maps raw parsed attributes into canonical structures.
    """
    def __init__(self):
        super().__init__("SchemaMapping")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.SCHEMA_MAPPED)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Map canonical attributes
            parser_res = context.parser_result or {}
            metadata_res = context.metadata or {}

            schema_service = EnterpriseSchemaMappingService()
            schema_obj = schema_service.map_schema(parser_res, metadata_res)

            context.canonical_record = schema_obj

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": schema_obj
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresSchemaStage = SchemaStage
