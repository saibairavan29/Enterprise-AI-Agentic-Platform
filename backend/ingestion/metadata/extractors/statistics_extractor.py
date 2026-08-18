import fitz
import os
import logging
from .base import BaseExtractor

logger = logging.getLogger('enterprise')

class StatisticsExtractor(BaseExtractor):
    """
    Extractor responsible for aggregating document structural statistics:
    total_pages, total_tables, total_images, total_words, total_characters,
    empty_pages, and scanned_pages.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        stats = {
            "total_pages": 1,
            "total_tables": 0,
            "total_images": 0,
            "total_words": 0,
            "total_characters": 0,
            "empty_pages": 0,
            "scanned_pages": 0
        }

        if not parser_output:
            return stats

        parser_type = parser_output.get("parser_type", "TEXT")
        content = parser_output.get("content", "")
        
        # If parser yielded empty content but OCR output is present
        if not content and ocr_output and ocr_output.get("text"):
            content = ocr_output["text"]

        if content:
            stats["total_characters"] = len(content)
            stats["total_words"] = len(content.split())

        # Resolve stats based on file type
        if parser_type == "PDF":
            parser_meta = parser_output.get("metadata", {})
            stats["total_pages"] = int(parser_meta.get("page_count") or parser_meta.get("pages", 1))
            
            structured_data = parser_output.get("structured_data", {})
            tables = structured_data.get("tables", [])
            stats["total_tables"] = len(tables)

            pages = structured_data.get("pages", [])
            empty_pages_count = 0
            scanned_pages_count = 0
            
            for p_txt in pages:
                stripped = p_txt.strip()
                if not stripped:
                    empty_pages_count += 1
                if len(stripped) < 20:
                    scanned_pages_count += 1

            stats["empty_pages"] = empty_pages_count
            stats["scanned_pages"] = scanned_pages_count

            # Extract image count from PDF using fitz if file is on disk
            stats["total_images"] = self._count_pdf_images(doc_obj)

        elif parser_type == "EXCEL":
            parser_meta = parser_output.get("metadata", {})
            sheet_count = int(parser_meta.get("sheet_count", 0))
            stats["total_pages"] = sheet_count
            stats["total_tables"] = sheet_count

        elif parser_type == "CSV":
            stats["total_tables"] = 1

        elif parser_type == "IMAGE":
            stats["total_images"] = 1

        return stats

    def _count_pdf_images(self, doc_obj):
        """
        Attempts to open the PDF file on disk using fitz to count embedded images.
        Does not throw exception if path is not resolved or not found.
        """
        doc_path = getattr(doc_obj, "file", None)
        file_path = None
        if doc_path and hasattr(doc_path, "path"):
            file_path = doc_path.path
        elif isinstance(doc_obj, dict):
            file_path = doc_obj.get("file_path") or doc_obj.get("stored_name")

        if not file_path or not os.path.exists(file_path):
            return 0

        try:
            image_count = 0
            with fitz.open(file_path) as doc:
                for page in doc:
                    image_count += len(page.get_images())
            return image_count
        except Exception as e:
            logger.warning(f"Could not count PDF images from path {file_path}: {str(e)}")
            return 0
