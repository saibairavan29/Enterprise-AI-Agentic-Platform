import logging
from .base import BaseStage
from ..pipeline.pipeline_context import PipelineContext
from ..pipeline.pipeline_state import PipelineState
from ingestion.ocr.services.pdf_ocr_service import PDFOCRService
from ingestion.ocr.services.image_ocr_service import ImageOCRService

logger = logging.getLogger('enterprise')

class OCRStage(BaseStage):
    """
    OCR Stage: Conditionally runs OCR for images or scanned PDFs.
    """
    def __init__(self):
        super().__init__("OCR")

    def execute(self, context: PipelineContext) -> dict:
        context.update_state(PipelineState.OCR_RUNNING)
        doc = context.uploaded_document
        if not doc:
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": ["Missing uploaded document object in context."],
                "output": {}
            }

        # Check if OCR is required
        is_scanned = False
        if context.parser_result:
            is_scanned = context.parser_result.get("metadata", {}).get("is_scanned", False)

        parser_type_lower = doc.parser_type.lower() if isinstance(doc.parser_type, str) else str(doc.parser_type).lower()
        requires_ocr = (parser_type_lower == "image") or (parser_type_lower == "pdf" and is_scanned)

        if not requires_ocr:
            return {
                "status": "SKIPPED",
                "warnings": [],
                "errors": [],
                "output": {}
            }

        try:
            file_path = doc.file.path
            if parser_type_lower == "pdf":
                ocr_service = PDFOCRService()
                output = ocr_service.execute(file_path)
            else:
                ocr_service = ImageOCRService()
                output = ocr_service.execute(file_path)

            context.ocr_result = output

            # Merge text content for down-stream metadata extractor runs
            if output and "text" in output:
                if context.parser_result:
                    context.parser_result["content"] = output["text"]

            return {
                "status": "SUCCESS",
                "warnings": output.get("warnings", []),
                "errors": output.get("errors", []),
                "output": output
            }
        except Exception as e:
            # Check if it is a missing Tesseract / OCR system binary error
            err_str = str(e).lower()
            if "tesseract" in err_str or "not installed" in err_str or "not found" in err_str:
                logger.warning(f"OCR execution skipped/failed gracefully (Tesseract missing): {str(e)}")
                output = {
                    "text": "",
                    "confidence": {
                        "average": 0.0,
                        "minimum": 0.0,
                        "maximum": 0.0,
                        "median": 0.0
                    },
                    "language": "eng",
                    "processing_time": 0.0,
                    "pages_processed": 0,
                    "engine": "Tesseract",
                    "status": "SKIPPED",
                    "ocr_status": "SKIPPED",
                    "warnings": [f"OCR skipped: Tesseract binary not installed on host: {str(e)}"],
                    "errors": [],
                    "execution_timestamp": None
                }
                context.ocr_result = output
                if context.parser_result:
                    context.parser_result["content"] = ""
                return {
                    "status": "SUCCESS",
                    "warnings": [f"OCR skipped (Tesseract missing): {str(e)}"],
                    "errors": [],
                    "output": output
                }
            return {
                "status": "FAILED",
                "warnings": [],
                "errors": [str(e)],
                "output": {}
            }
PostgresOCRStage = OCRStage
