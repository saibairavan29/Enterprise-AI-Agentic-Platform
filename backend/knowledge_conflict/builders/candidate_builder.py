import uuid
from datetime import datetime
from ..models import KnowledgeCandidate

class CandidateBuilder:
    """
    Builder class for constructing KnowledgeCandidate model instances with appropriate
    traceability IDs, fingerprints, and tracking metadata.
    """
    @staticmethod
    def build(data: dict, batch_id: str) -> KnowledgeCandidate:
        """
        Assembles a KnowledgeCandidate database model instance from raw strategy output maps.
        """
        # Read parameters, default none values safely
        source_doc_id = data.get("source_document_id")
        target_doc_id = data.get("target_document_id")
        
        source_seg_id = data.get("source_segment_id")
        target_seg_id = data.get("target_segment_id")
        
        source_text = data.get("source_text", "")
        target_text = data.get("target_text", "")
        
        source_page = data.get("source_page")
        target_page = data.get("target_page")
        
        source_section = data.get("source_section")
        target_section = data.get("target_section")
        
        strategy_used = data.get("strategy_used", "GenericStrategy")
        strategy_confidence = data.get("strategy_confidence", 50.0)
        entity_type = data.get("entity_type", "Generic")
        candidate_hash = data.get("candidate_hash", "")
        
        meta = data.get("metadata", {})
        # Enforce pipeline tracking indicators
        meta_enriched = {
            **meta,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "3.0",
            "strategy_version": "1.0"
        }

        return KnowledgeCandidate(
            candidate_id=uuid.uuid4(),
            batch_id=batch_id,
            candidate_hash=candidate_hash,
            source_document_id=source_doc_id,
            target_document_id=target_doc_id,
            source_segment_id=source_seg_id,
            target_segment_id=target_seg_id,
            source_text=source_text,
            target_text=target_text,
            source_page=source_page,
            target_page=target_page,
            source_section=source_section,
            target_section=target_section,
            strategy_used=strategy_used,
            strategy_confidence=strategy_confidence,
            entity_type=entity_type,
            status='GENERATED',
            metadata=meta_enriched
        )
