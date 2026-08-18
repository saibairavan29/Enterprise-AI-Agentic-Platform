from .base import BaseExtractor

class TextExtractor(BaseExtractor):
    """
    Extractor responsible for text statistics:
    character_count, word_count, and encoding.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "character_count": 0,
            "word_count": 0,
            "encoding": "utf-8"
        }

        content_text = ""
        if parser_output and parser_output.get("content"):
            content_text = parser_output["content"]
        
        # If parser yielded empty content but OCR ran successfully, parse the OCR text
        if not content_text and ocr_output and ocr_output.get("text"):
            content_text = ocr_output["text"]

        if content_text:
            res["character_count"] = len(content_text)
            res["word_count"] = len(content_text.split())

        if parser_output:
            parser_meta = parser_output.get("metadata", {})
            res["encoding"] = parser_meta.get("encoding") or "utf-8"

        return res
