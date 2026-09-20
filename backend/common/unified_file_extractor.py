import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('enterprise')

class UnifiedFileExtractor:
    """
    Authoritative single-source file content extractor.
    Resolves physical disk files for KnowledgeDocument objects or path strings,
    and executes appropriate concrete parsers (PDFParser with OCR, ExcelParser across all sheets,
    ImageParser with OCR, CSVParser, DocxParser, TextParser, JSONParser).
    """

    @classmethod
    def resolve_physical_file_path(cls, document_or_path) -> Optional[str]:
        """
        Resolves the absolute physical file path on disk for a KnowledgeDocument or string path.
        """
        if not document_or_path:
            return None

        if isinstance(document_or_path, str):
            if os.path.isabs(document_or_path) and os.path.exists(document_or_path):
                return document_or_path
            
            from django.conf import settings
            base_dir = getattr(settings, 'BASE_DIR', '')
            candidates = [
                document_or_path,
                os.path.join(base_dir, document_or_path),
                os.path.join(base_dir, "Uploads", document_or_path),
                os.path.join(base_dir, "Uploads", "raw", os.path.basename(document_or_path)),
                os.path.join(os.path.dirname(base_dir), "Uploads", "raw", os.path.basename(document_or_path)),
                os.path.join(base_dir, "test_files", os.path.basename(document_or_path))
            ]
            for c in candidates:
                if c and os.path.exists(c):
                    return os.path.abspath(c)
            return None

        # Document is a KnowledgeDocument instance
        doc = document_or_path
        file_path = None

        if hasattr(doc, 'source_document') and doc.source_document and getattr(doc.source_document, 'file', None):
            try:
                if os.path.exists(doc.source_document.file.path):
                    file_path = doc.source_document.file.path
            except Exception:
                pass

        if not file_path and getattr(doc, 'metadata', None) and isinstance(doc.metadata, dict):
            file_meta = doc.metadata.get("file", {}) if isinstance(doc.metadata.get("file"), dict) else {}
            source_meta = doc.metadata.get("source", {}) if isinstance(doc.metadata.get("source"), dict) else {}
            stored_name = (file_meta.get("stored_name") if isinstance(file_meta, dict) else "") or \
                          (source_meta.get("file_path") if isinstance(source_meta, dict) else "") or \
                          (source_meta.get("storage_location") if isinstance(source_meta, dict) else "") or ""
            
            if stored_name:
                from django.conf import settings
                base_dir = getattr(settings, 'BASE_DIR', '')
                clean_name = os.path.basename(stored_name)
                possible_paths = [
                    stored_name,
                    os.path.join(base_dir, stored_name),
                    os.path.join(base_dir, "Uploads", stored_name),
                    os.path.join(base_dir, "Uploads", "raw", clean_name),
                    os.path.join(os.path.dirname(base_dir), "Uploads", "raw", clean_name),
                    os.path.join(base_dir, "test_files", clean_name)
                ]
                for p in possible_paths:
                    if p and os.path.exists(p):
                        file_path = os.path.abspath(p)
                        break

        if not file_path and getattr(doc, 'title', None):
            from django.conf import settings
            base_dir = getattr(settings, 'BASE_DIR', '')
            clean_title = doc.title.strip()
            title_name = os.path.basename(clean_title)
            possible_paths = [
                os.path.join(base_dir, "Uploads", "raw", title_name),
                os.path.join(base_dir, "Uploads", title_name),
                os.path.join(os.path.dirname(base_dir), "Uploads", "raw", title_name),
                os.path.join(base_dir, "test_files", title_name)
            ]
            for p in possible_paths:
                if p and os.path.exists(p):
                    file_path = os.path.abspath(p)
                    break

        return file_path

    _file_extracted_cache = {}

    @classmethod
    def extract(cls, document_or_path) -> Dict[str, Any]:
        """
        Executes physical file content parsing with memory caching.
        """
        file_path = cls.resolve_physical_file_path(document_or_path)
        if file_path and file_path in cls._file_extracted_cache:
            return cls._file_extracted_cache[file_path]
            
        title = getattr(document_or_path, 'title', str(document_or_path)) if not isinstance(document_or_path, str) else os.path.basename(document_or_path)
        
        fallback_res = {
            "file_path": file_path,
            "file_type": "generic",
            "content": getattr(document_or_path, 'raw_content', "") if hasattr(document_or_path, 'raw_content') else "",
            "structured_data": {},
            "metadata": {},
            "sheet_names": [],
            "ocr_used": False
        }

        if not file_path or not os.path.exists(file_path):
            return fallback_res

        ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        try:
            if ext == 'pdf':
                from ingestion.parsers.pdf_parser import PDFParser
                parser_res = PDFParser().parse(file_path)
                meta = parser_res.get("metadata", {})
                return {
                    "file_path": file_path,
                    "file_type": "pdf",
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", {}),
                    "metadata": meta,
                    "sheet_names": [],
                    "ocr_used": meta.get("ocr_success", False) or meta.get("ocr_attempted", False)
                }

            elif ext in ['xlsx', 'xls']:
                from ingestion.parsers.excel_parser import ExcelParser
                parser_res = ExcelParser().parse(file_path)
                meta = parser_res.get("metadata", {})
                sheets = meta.get("sheets", [])
                return {
                    "file_path": file_path,
                    "file_type": "excel",
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", {}),
                    "metadata": meta,
                    "sheet_names": sheets,
                    "ocr_used": False
                }

            elif ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
                from ingestion.parsers.image_parser import ImageParser
                parser_res = ImageParser().parse(file_path)
                meta = parser_res.get("metadata", {})
                return {
                    "file_path": file_path,
                    "file_type": "image",
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", {}),
                    "metadata": meta,
                    "sheet_names": [],
                    "ocr_used": meta.get("ocr_status") == "SUCCESS" or bool(parser_res.get("content"))
                }

            elif ext == 'csv':
                from ingestion.parsers.csv_parser import CSVParser
                parser_res = CSVParser().parse(file_path)
                return {
                    "file_path": file_path,
                    "file_type": "csv",
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", []),
                    "metadata": parser_res.get("metadata", {}),
                    "sheet_names": [],
                    "ocr_used": False
                }

            elif ext in ['docx', 'doc']:
                from ingestion.parsers.docx_parser import DocxParser
                parser_res = DocxParser().parse(file_path)
                return {
                    "file_path": file_path,
                    "file_type": "docx",
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", {}),
                    "metadata": parser_res.get("metadata", {}),
                    "sheet_names": [],
                    "ocr_used": False
                }

            elif ext in ['txt', 'md', 'json']:
                from ingestion.parsers.text_parser import TextParser
                from ingestion.parsers.json_parser import JSONParser
                if ext == 'json':
                    parser_res = JSONParser().parse(file_path)
                else:
                    parser_res = TextParser().parse(file_path)
                return {
                    "file_path": file_path,
                    "file_type": ext,
                    "content": parser_res.get("content", ""),
                    "structured_data": parser_res.get("structured_data", {}),
                    "metadata": parser_res.get("metadata", {}),
                    "sheet_names": [],
                    "ocr_used": False
                }

        except Exception as e:
            logger.error(f"UnifiedFileExtractor failed for {file_path}: {e}", exc_info=True)

        return fallback_res
