from .base import BaseExtractor

class OCRExtractor(BaseExtractor):
    """
    Extractor responsible for mapping OCR execution logs:
    engine, language, word confidences, timing, status, and warnings.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        if not ocr_output:
            return {
                "engine": None,
                "language": None,
                "confidence": {
                    "average": None,
                    "minimum": None,
                    "maximum": None,
                    "median": None
                },
                "pages_processed": 0,
                "processing_time": None,
                "ocr_status": "SKIPPED",
                "warnings": [],
                "errors": [],
                "execution_timestamp": None
            }

        conf_data = ocr_output.get("confidence", {})
        
        return {
            "engine": ocr_output.get("engine", "Tesseract"),
            "language": ocr_output.get("language", "eng"),
            "confidence": {
                "average": conf_data.get("average") if conf_data.get("average") is not None else None,
                "minimum": conf_data.get("minimum") if conf_data.get("minimum") is not None else None,
                "maximum": conf_data.get("maximum") if conf_data.get("maximum") is not None else None,
                "median": conf_data.get("median") if conf_data.get("median") is not None else None
            },
            "pages_processed": int(ocr_output.get("pages_processed", 1)),
            "processing_time": ocr_output.get("processing_time"),
            "ocr_status": ocr_output.get("ocr_status") or ocr_output.get("status") or "OCR_COMPLETED",
            "warnings": ocr_output.get("warnings", []),
            "errors": ocr_output.get("errors", []),
            "execution_timestamp": ocr_output.get("execution_timestamp")
        }
