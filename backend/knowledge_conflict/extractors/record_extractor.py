from .base import BaseExtractor
from ..exceptions.exceptions import ExtractorException

class RecordExtractor(BaseExtractor):
    """
    Extractor strategy for converting KnowledgeRecord data (canonical_data, additional_fields)
    into structured textual segments for comparative conflict analysis.
    """
    def extract(self, record) -> list:
        if not record:
            raise ExtractorException("Record object cannot be None.")
            
        segments = []
        rec_id = str(record.id)
        doc_id = str(record.knowledge_document_id)
        entity_type = record.entity_type or "Generic"
        
        canonical = record.canonical_data or {}
        additional = record.additional_fields or {}
        
        # 1. Compile the entire record as a unified block segment
        field_strs = []
        for key, val in canonical.items():
            field_strs.append(f"{key}: {val}")
        for key, val in additional.items():
            field_strs.append(f"{key}: {val}")
            
        full_text = f"Entity Type: {entity_type} | " + " | ".join(field_strs)
        segments.append({
            "segment_id": f"rec-{rec_id}-full",
            "text": full_text,
            "page": None,
            "section": "Structured Record",
            "metadata": {
                "source_field": "full_record",
                "entity_type": entity_type,
                "document_id": doc_id,
                "record_id": rec_id,
                "canonical_keys": list(canonical.keys())
            }
        })
        
        # 2. Extract individual text fields as isolated segments
        for key, val in canonical.items():
            if isinstance(val, (str, int, float)) and not isinstance(val, bool):
                segments.append({
                    "segment_id": f"rec-{rec_id}-field-{key}",
                    "text": f"{key}: {val}",
                    "page": None,
                    "section": f"Record Canonical Field - {key}",
                    "metadata": {
                        "source_field": f"canonical_data.{key}",
                        "entity_type": entity_type,
                        "document_id": doc_id,
                        "record_id": rec_id,
                        "field_name": key,
                        "field_value": val
                    }
                })
                
        return segments
