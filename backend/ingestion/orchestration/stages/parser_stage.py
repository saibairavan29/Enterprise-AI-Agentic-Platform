from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ingestion.router.dispatcher import ParserDispatcher

class ParserStage(BaseStage):
    """
    Parser Stage: Resolves appropriate document parser and parses text/tables/metadata.
    """
    def __init__(self):
        super().__init__("Parser")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.PARSING)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Resolve parser type from document model
            parser_type = doc.parser_type
            parser = ParserDispatcher.get_parser(parser_type)
            
            # Execute parsing on the physical file path
            file_path = doc.file.path
            output = parser.parse(file_path)

            context.parser_result = output

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": output
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresParserStage = ParserStage
