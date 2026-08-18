from django.core.exceptions import ValidationError
from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from common.validators import validate_file_extension, validate_mime_type

class ValidationStage(BaseStage):
    """
    Validation Stage: Runs physical file formats, sizes, and signature checks.
    """
    def __init__(self):
        super().__init__("Validation")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.VALIDATED)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        try:
            # Resolve extension
            filename = doc.original_name or doc.file.name
            ext = validate_file_extension(filename)
            
            # Signature check
            if doc.file:
                validate_mime_type(doc.file, ext)

            return {
                "status": "SUCCESS",
                "warnings": [],
                "errors": [],
                "output": {"validated": True}
            }
        except ValidationError as ve:
            err_msgs = ve.messages if hasattr(ve, 'messages') else [str(ve)]
            context.warnings.extend(err_msgs)
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": err_msgs,
                "output": {}
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
