from .base import BaseExtractor
from ..exceptions.exceptions import ExtractorException
from common.unified_file_extractor import UnifiedFileExtractor

class DocumentExtractor(BaseExtractor):
    """
    Extractor strategy for pulling raw text, OCR text, multi-sheet Excel content,
    and metadata strings out of KnowledgeDocument objects.
    """
    _segment_cache = {}

    def extract(self, document) -> list:
        if not document:
            raise ExtractorException("Document object cannot be None.")
            
        doc_id = str(document.id)
        cache_key = f"{doc_id}_v{getattr(document, 'current_version', 1)}"
        if cache_key in self._segment_cache:
            return self._segment_cache[cache_key]

        segments = []

        # 1. Run Unified File Extractor on physical disk file (PDF OCR, Excel multi-sheet, Image OCR, etc.)
        extracted_data = UnifiedFileExtractor.extract(document)
        parsed_content = extracted_data.get("content", "").strip()
        structured_data = extracted_data.get("structured_data", {})
        file_type = extracted_data.get("file_type", "")

        # 2. Extract multi-sheet Excel content
        if file_type == 'excel' and isinstance(structured_data, dict) and structured_data:
            for sheet_name, sheet_records in structured_data.items():
                if isinstance(sheet_records, list) and sheet_records:
                    sheet_lines = []
                    for row_idx, r in enumerate(sheet_records[:200]):
                        if isinstance(r, dict):
                            vals = [f"{k}: {v}" for k, v in r.items() if v is not None and str(v).strip() != '']
                            if vals:
                                sheet_lines.append(f"Row {row_idx+1}: " + " | ".join(vals))
                    sheet_text = f"Worksheet [{sheet_name}]:\n" + "\n".join(sheet_lines)
                    segments.append({
                        "segment_id": f"{doc_id}-sheet-{sheet_name}",
                        "text": sheet_text,
                        "page": 1,
                        "section": f"Worksheet: {sheet_name}",
                        "metadata": {
                            "source_field": "sheet_content",
                            "document_id": doc_id,
                            "title": document.title,
                            "sheet_name": sheet_name,
                            "version": document.current_version
                        }
                    })

        # 3. Extract PDF pages with OCR
        elif file_type == 'pdf' and isinstance(structured_data, dict) and 'pages' in structured_data:
            pages = structured_data.get('pages', [])
            for page_idx, page_str in enumerate(pages):
                if page_str and page_str.strip():
                    segments.append({
                        "segment_id": f"{doc_id}-page-{page_idx+1}",
                        "text": page_str.strip(),
                        "page": page_idx + 1,
                        "section": f"Page {page_idx+1}",
                        "metadata": {
                            "source_field": "pdf_page",
                            "document_id": doc_id,
                            "title": document.title,
                            "page": page_idx + 1,
                            "ocr_used": extracted_data.get("ocr_used", False)
                        }
                    })

        # 4. Extract from parsed content or raw_content fallback
        full_text = parsed_content or (document.raw_content or "").strip()
        if full_text and not segments:
            segments.append({
                "segment_id": f"{doc_id}-content",
                "text": full_text,
                "page": 1,
                "section": "Document Content",
                "metadata": {
                    "source_field": "file_content",
                    "document_id": doc_id,
                    "title": document.title,
                    "version": document.current_version,
                    "ocr_used": extracted_data.get("ocr_used", False)
                }
            })

        # 5. Ensure document metadata is attached to all extracted segments
        meta_dict = document.metadata or {}
        for seg in segments:
            seg["metadata"].update({
                "repository_type": meta_dict.get("repository_type"),
                "folder_name": meta_dict.get("folder_name")
            })

        self._segment_cache[cache_key] = segments
        return segments
