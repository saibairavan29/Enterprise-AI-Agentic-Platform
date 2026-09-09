import json
from typing import Dict, Any, Optional

class EvidenceItem:
    """
    Unified Internal Evidence Representation Model.
    Preserves source provenance, document identity, extraction method, confidence,
    and typed evidence representation without forcing all source types into flat text strings.
    """
    def __init__(
        self,
        source_id: str,
        filename: str,
        document_id: Optional[str] = None,
        page_or_section: Optional[str] = None,
        content: Any = "",
        content_type: str = "DOCUMENT_TEXT", # DOCUMENT_TEXT, OCR_TEXT, STRUCTURED_TABLE, STRUCTURED_RECORD, CALCULATION_RESULT, KG_EVIDENCE
        extraction_method: str = "DIRECT_PARSER",
        confidence: str = "100.0%",
        metadata: Optional[Dict[str, Any]] = None,
        evidence_type: Optional[str] = None
    ):
        self.source_id = source_id
        self.filename = filename
        self.document_id = document_id
        self.page_or_section = page_or_section
        self.content = content
        self.content_type = content_type
        self.evidence_type = evidence_type or content_type
        self.extraction_method = extraction_method
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "document_id": self.document_id,
            "page_or_section": self.page_or_section,
            "content": self.content,
            "content_type": self.content_type,
            "evidence_type": self.evidence_type,
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

    def to_prompt_text(self) -> str:
        """
        Formats evidence item cleanly for LLM context without internal orchestration labels.
        """
        if self.content_type == "KEY_VALUE" and isinstance(self.content, dict):
            kv_lines = [f"{k}: {v}" for k, v in self.content.items()]
            return f"Key-Value Data ({self.filename}):\n" + "\n".join(kv_lines)
        elif self.content_type == "TABLE" and isinstance(self.content, list):
            table_str = ""
            for row in self.content:
                if isinstance(row, list):
                    table_str += " | ".join([str(c) for c in row if c is not None]) + "\n"
                elif isinstance(row, dict):
                    table_str += " | ".join([f"{k}: {v}" for k, v in row.items() if v is not None]) + "\n"
            return f"Structured Table ({self.filename} - {self.page_or_section or 'Data'}):\n" + table_str.strip()
        elif self.content_type == "ANALYTICAL_RESULT":
            return f"Calculated Fact ({self.filename}): {self.content}"
        elif self.content_type == "KG_FACT":
            return f"Enterprise Connection ({self.filename}): {self.content}"
        elif isinstance(self.content, dict):
            return f"Structured Item ({self.filename}):\n" + json.dumps(self.content, indent=2)
        else:
            return f"Source Content ({self.filename} - {self.page_or_section or 'Main'}):\n{str(self.content).strip()}"
