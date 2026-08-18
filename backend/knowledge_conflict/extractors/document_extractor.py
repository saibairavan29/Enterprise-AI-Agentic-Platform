from .base import BaseExtractor
from ..exceptions.exceptions import ExtractorException

class DocumentExtractor(BaseExtractor):
    """
    Extractor strategy for pulling raw text and metadata strings out of KnowledgeDocument objects.
    """
    def extract(self, document) -> list:
        if not document:
            raise ExtractorException("Document object cannot be None.")
            
        segments = []
        doc_id = str(document.id)
        
        # 1. Extract from raw_content
        raw_text = document.raw_content or ""
        if raw_text.strip():
            segments.append({
                "segment_id": f"{doc_id}-raw",
                "text": raw_text,
                "page": 1,
                "section": "Raw Content",
                "metadata": {
                    "source_field": "raw_content",
                    "title": document.title,
                    "version": document.current_version
                }
            })
            
        # 2. Extract specific metadata descriptions
        meta_dict = document.metadata or {}
        for key, val in meta_dict.items():
            if isinstance(val, str) and val.strip():
                segments.append({
                    "segment_id": f"{doc_id}-meta-{key}",
                    "text": f"{key}: {val}",
                    "page": None,
                    "section": "Metadata Header",
                    "metadata": {
                        "source_field": f"metadata.{key}",
                        "title": document.title,
                        "version": document.current_version
                    }
                })
                
        return segments
