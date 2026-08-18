from .base import BaseExtractor

class LineageExtractor(BaseExtractor):
    """
    Extractor responsible for document parser tracking:
    document_id, parent_document, parser, parser_version, ocr_applied,
    metadata_version, and processing_stage.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "document_id": None,
            "parent_document": None,
            "parser": None,
            "parser_version": "1.0.0",
            "ocr_applied": False,
            "metadata_version": "1.0",
            "processing_stage": "METADATA_EXTRACTED"
        }

        if doc_obj:
            doc_id = getattr(doc_obj, "id", None) or getattr(doc_obj, "pk", None)
            if doc_id:
                res["document_id"] = str(doc_id)
            elif isinstance(doc_obj, dict):
                res["document_id"] = str(doc_obj.get("document_id") or doc_obj.get("id", ""))

        if parser_output:
            parser_type = parser_output.get("parser_type", "TEXT")
            res["parser"] = f"{parser_type}Parser"

        if ocr_output and ocr_output.get("ocr_status") != "SKIPPED":
            res["ocr_applied"] = True

        return res
