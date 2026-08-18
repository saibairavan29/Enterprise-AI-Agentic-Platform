from .base import BaseExtractor

class PDFExtractor(BaseExtractor):
    """
    Extractor responsible for PDF-specific properties:
    title, author, subject, keywords, pdf version, and page count.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "title": None,
            "author": None,
            "subject": None,
            "keywords": None,
            "version": None,
            "page_count": 0
        }
        
        if not parser_output or parser_output.get("parser_type") != "PDF":
            return res

        parser_meta = parser_output.get("metadata", {})
        res["title"] = parser_meta.get("title") or None
        res["author"] = parser_meta.get("author") or None
        res["subject"] = parser_meta.get("subject") or None
        res["keywords"] = parser_meta.get("keywords") or None
        res["version"] = parser_meta.get("version") or parser_meta.get("pdf_version") or None
        res["page_count"] = int(parser_meta.get("page_count") or parser_meta.get("pages", 0))

        return res
