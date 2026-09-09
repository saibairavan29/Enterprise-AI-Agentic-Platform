import hashlib
from .base import BasePairingStrategy
from ..registry.strategy_registry import StrategyRegistry
from ..exceptions.exceptions import CandidateGenerationException
from repository.models import KnowledgeDocumentVersion, KnowledgeRecord
from ..preprocessors.segmenter import RegexSegmenter

def should_pair_records(rec1, rec2) -> bool:
    if not rec1 or not rec2:
        return True
    if rec1.id == rec2.id:
        return False
        
    data1 = rec1.canonical_data or {}
    data2 = rec2.canonical_data or {}
    
    # Check for primary identifiers in common keys
    common_keys = set(data1.keys()).intersection(set(data2.keys()))
    id_fields = ["employee_id", "id", "uuid", "email", "code", "number"]
    
    found_id_key = None
    for field in id_fields:
        for k in common_keys:
            if k.lower() == field.lower():
                found_id_key = k
                break
        if found_id_key:
            break
            
    if found_id_key:
        val1 = str(data1.get(found_id_key, "")).strip().lower()
        val2 = str(data2.get(found_id_key, "")).strip().lower()
        # If both values are non-empty, they MUST match
        if val1 and val2:
            return val1 == val2
            
    return True

def get_record_by_id(rec_id, records_db):
    try:
        return records_db.get(int(rec_id))
    except (ValueError, TypeError):
        return records_db.get(rec_id)

class SameVersionStrategy(BasePairingStrategy):
    """
    Pairs text segments of the same KnowledgeDocument across its different historical versions.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        segmenter = RegexSegmenter()
        
        for doc in documents:
            doc_id = str(doc.id)
            # Fetch all historical versions of this knowledge document
            versions = list(KnowledgeDocumentVersion.objects.filter(knowledge_document=doc).order_by('version'))
            if len(versions) < 2:
                continue
                
            # Parse segments for each version
            version_segments = {}
            for ver in versions:
                ver_text = ver.raw_content or ""
                ver_key = f"ver-{ver.version}"
                version_segments[ver_key] = segmenter.segment(ver_text, source_id=f"{doc_id}-v{ver.version}")
                
            # Pair segments of version V_i with version V_j (for all i < j)
            ver_keys = list(version_segments.keys())
            for i in range(len(ver_keys)):
                for j in range(i + 1, len(ver_keys)):
                    v1_key = ver_keys[i]
                    v2_key = ver_keys[j]
                    
                    segs1 = version_segments[v1_key]
                    segs2 = version_segments[v2_key]
                    
                    # For simplicity, pair sentences by index or compare sentence pairs
                    # To keep it standard, pair corresponding sentence/paragraph offsets
                    min_len = min(len(segs1), len(segs2))
                    for k in range(min_len):
                        s1 = segs1[k]
                        s2 = segs2[k]
                        
                        # Only pair if content differs
                        if s1["text"].strip().lower() != s2["text"].strip().lower():
                            pairs.append({
                                "source_document_id": doc.id,
                                "target_document_id": doc.id,
                                "source_segment_id": s1["segment_id"],
                                "target_segment_id": s2["segment_id"],
                                "source_text": s1["text"],
                                "target_text": s2["text"],
                                "source_page": s1.get("page", 1),
                                "target_page": s2.get("page", 1),
                                "source_section": s1.get("section", "Version History"),
                                "target_section": s2.get("section", "Version History"),
                                "strategy_used": "SameVersionStrategy",
                                "strategy_confidence": self.confidence,
                                "entity_type": "DocumentVersion",
                                "metadata": {
                                    "source_version": v1_key,
                                    "target_version": v2_key,
                                    "segment_index": k
                                }
                            })
        return pairs


class SameEntityTypeStrategy(BasePairingStrategy):
    """
    Pairs structured record segments sharing identical entity_type parameters across documents.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        records_db = {r.id: r for r in records}
        
        # Filter full structured segments of records
        record_segs = [s for s in segments if s["segment_id"].startswith("rec-") and s["segment_id"].endswith("-full")]
        
        # Group segments by entity_type
        by_entity = {}
        for seg in record_segs:
            entity = seg["metadata"].get("entity_type", "Generic")
            by_entity.setdefault(entity, []).append(seg)
            
        # Pair segments within the same entity type
        for entity, segs in by_entity.items():
            for i in range(len(segs)):
                for j in range(i + 1, len(segs)):
                    s1 = segs[i]
                    s2 = segs[j]
                    
                    # Ensure records are from different documents or are different records
                    if s1["metadata"]["record_id"] != s2["metadata"]["record_id"]:
                        rec1 = get_record_by_id(s1["metadata"]["record_id"], records_db)
                        rec2 = get_record_by_id(s2["metadata"]["record_id"], records_db)
                        if not should_pair_records(rec1, rec2):
                            continue
                            
                        pairs.append({
                            "source_document_id": s1["metadata"].get("document_id") or (rec1.knowledge_document_id if rec1 else None),
                            "target_document_id": s2["metadata"].get("document_id") or (rec2.knowledge_document_id if rec2 else None),
                            "source_segment_id": s1["segment_id"],
                            "target_segment_id": s2["segment_id"],
                            "source_text": s1["text"],
                            "target_text": s2["text"],
                            "source_page": None,
                            "target_page": None,
                            "source_section": s1.get("section"),
                            "target_section": s2.get("section"),
                            "strategy_used": "SameEntityTypeStrategy",
                            "strategy_confidence": self.confidence,
                            "entity_type": entity,
                            "metadata": {
                                "source_record_id": s1["metadata"]["record_id"],
                                "target_record_id": s2["metadata"]["record_id"]
                            }
                        })
        return pairs


class SameDepartmentStrategy(BasePairingStrategy):
    """
    Pairs structured record segments sharing identical department values in canonical_data.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        records_db = {r.id: r for r in records}
        
        # Filter record segment full blocks
        record_segs = [s for s in segments if s["segment_id"].startswith("rec-") and s["segment_id"].endswith("-full")]
        
        # Group segments by department value
        by_dept = {}
        for seg in record_segs:
            rec_obj = get_record_by_id(seg["metadata"]["record_id"], records_db)
            if rec_obj:
                dept = rec_obj.canonical_data.get("department", "")
                if dept and str(dept).strip():
                    by_dept.setdefault(str(dept).strip().lower(), []).append((seg, dept))
                    
        # Pair segments within the same department
        for dept_val, items in by_dept.items():
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    s1, dept1 = items[i]
                    s2, dept2 = items[j]
                    
                    if s1["metadata"]["record_id"] != s2["metadata"]["record_id"]:
                        rec1 = get_record_by_id(s1["metadata"]["record_id"], records_db)
                        rec2 = get_record_by_id(s2["metadata"]["record_id"], records_db)
                        if not should_pair_records(rec1, rec2):
                            continue
                            
                        pairs.append({
                            "source_document_id": s1["metadata"].get("document_id") or (rec1.knowledge_document_id if rec1 else None),
                            "target_document_id": s2["metadata"].get("document_id") or (rec2.knowledge_document_id if rec2 else None),
                            "source_segment_id": s1["segment_id"],
                            "target_segment_id": s2["segment_id"],
                            "source_text": s1["text"],
                            "target_text": s2["text"],
                            "source_page": None,
                            "target_page": None,
                            "source_section": s1.get("section"),
                            "target_section": s2.get("section"),
                            "strategy_used": "SameDepartmentStrategy",
                            "strategy_confidence": self.confidence,
                            "entity_type": s1["metadata"].get("entity_type", "Generic"),
                            "metadata": {
                                "department": dept1,
                                "source_record_id": s1["metadata"]["record_id"],
                                "target_record_id": s2["metadata"]["record_id"]
                            }
                        })
        return pairs


class SameTitleStrategy(BasePairingStrategy):
    """
    Pairs document paragraphs/sentences where source and target documents share identical titles.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        
        # Group documents by title
        by_title = {}
        for doc in documents:
            by_title.setdefault(doc.title.strip().lower(), []).append(doc)
            
        # Pair segments of documents sharing identical titles
        for title, docs in by_title.items():
            if len(docs) < 2:
                continue
                
            for i in range(len(docs)):
                for j in range(i + 1, len(docs)):
                    d1 = docs[i]
                    d2 = docs[j]
                    
                    # Fetch segments belonging to d1 and d2
                    segs1 = [s for s in segments if s["segment_id"].startswith(f"{d1.id}-")]
                    segs2 = [s for s in segments if s["segment_id"].startswith(f"{d2.id}-")]
                    
                    for s1 in segs1:
                        for s2 in segs2:
                            # Only compare similar segment types
                            if s1["type"] == s2["type"] and s1["text"].strip().lower() != s2["text"].strip().lower():
                                pairs.append({
                                    "source_document_id": d1.id,
                                    "target_document_id": d2.id,
                                    "source_segment_id": s1["segment_id"],
                                    "target_segment_id": s2["segment_id"],
                                    "source_text": s1["text"],
                                    "target_text": s2["text"],
                                    "source_page": s1.get("page"),
                                    "target_page": s2.get("page"),
                                    "source_section": s1.get("section"),
                                    "target_section": s2.get("section"),
                                    "strategy_used": "SameTitleStrategy",
                                    "strategy_confidence": self.confidence,
                                    "entity_type": "DocumentSegment",
                                    "metadata": {
                                        "title": d1.title,
                                        "source_type": s1["type"]
                                    }
                                })
        return pairs


class SimilarityWindowStrategy(BasePairingStrategy):
    """
    Pairs records where numeric fields (e.g. salary) overlap within configured windows.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        records_db = {r.id: r for r in records}
        record_segs = [s for s in segments if s["segment_id"].startswith("rec-") and s["segment_id"].endswith("-full")]
        
        numeric_fields = self.config.get("numeric_fields", {"salary": {"window": 1000.0}})
        
        for field, params in numeric_fields.items():
            window = params.get("window", 1000.0)
            
            # Find records with valid numeric fields
            valid_items = []
            for seg in record_segs:
                rec_obj = get_record_by_id(seg["metadata"]["record_id"], records_db)
                if rec_obj:
                    val = rec_obj.canonical_data.get(field)
                    try:
                        if val is not None:
                            valid_items.append((seg, float(val)))
                    except (ValueError, TypeError):
                        continue
                        
            # Pair records where difference is within sliding window
            for i in range(len(valid_items)):
                for j in range(i + 1, len(valid_items)):
                    item1, val1 = valid_items[i]
                    item2, val2 = valid_items[j]
                    
                    if item1["metadata"]["record_id"] != item2["metadata"]["record_id"]:
                        rec1 = get_record_by_id(item1["metadata"]["record_id"], records_db)
                        rec2 = get_record_by_id(item2["metadata"]["record_id"], records_db)
                        if not should_pair_records(rec1, rec2):
                            continue
                            
                        if abs(val1 - val2) <= window:
                            pairs.append({
                                "source_document_id": item1["metadata"].get("document_id") or (rec1.knowledge_document_id if rec1 else None),
                                "target_document_id": item2["metadata"].get("document_id") or (rec2.knowledge_document_id if rec2 else None),
                                "source_segment_id": item1["segment_id"],
                                "target_segment_id": item2["segment_id"],
                                "source_text": item1["text"],
                                "target_text": item2["text"],
                                "source_page": None,
                                "target_page": None,
                                "source_section": item1.get("section"),
                                "target_section": item2.get("section"),
                                "strategy_used": "SimilarityWindowStrategy",
                                "strategy_confidence": self.confidence,
                                "entity_type": item1["metadata"].get("entity_type", "Generic"),
                                "metadata": {
                                    "field": field,
                                    "source_value": val1,
                                    "target_value": val2,
                                    "difference": abs(val1 - val2),
                                    "source_record_id": item1["metadata"]["record_id"],
                                    "target_record_id": item2["metadata"]["record_id"]
                                }
                            })
        return pairs


class UniversalCrossCheckStrategy(BasePairingStrategy):
    """
    Generic, template-independent cross-check strategy.
    Performs cross-file and cross-record property comparison across all ingested documents
    and canonical database records without relying on rigid template schemas.
    """
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        pairs = []
        records_db = {r.id: r for r in records}
        record_segs = [s for s in segments if s["segment_id"].startswith("rec-") and s["segment_id"].endswith("-full")]
        doc_segs = [s for s in segments if not s["segment_id"].startswith("rec-")]

        # 1. Generic Cross-Check between Records across files & entities
        for i in range(len(record_segs)):
            for j in range(i + 1, len(record_segs)):
                s1 = record_segs[i]
                s2 = record_segs[j]
                
                rec1_id = s1["metadata"].get("record_id")
                rec2_id = s2["metadata"].get("record_id")
                if rec1_id == rec2_id:
                    continue
                    
                rec1 = get_record_by_id(rec1_id, records_db)
                rec2 = get_record_by_id(rec2_id, records_db)
                
                d1 = (rec1.canonical_data if rec1 else {}) or {}
                d2 = (rec2.canonical_data if rec2 else {}) or {}
                
                common_keys = set(d1.keys()).intersection(set(d2.keys()))
                
                # Pair if records share any canonical keys or schema fields, or are from different files
                should_pair = False
                reason = "Cross-Record Property Check"
                
                if common_keys:
                    should_pair = True
                    reason = f"Common properties: {', '.join(list(common_keys)[:3])}"
                elif str(s1["metadata"].get("document_id")) != str(s2["metadata"].get("document_id")):
                    should_pair = True
                    reason = "Cross-Document Record Check"
                    
                if should_pair:
                    pairs.append({
                        "source_document_id": s1["metadata"].get("document_id") or (rec1.knowledge_document_id if rec1 else None),
                        "target_document_id": s2["metadata"].get("document_id") or (rec2.knowledge_document_id if rec2 else None),
                        "source_segment_id": s1["segment_id"],
                        "target_segment_id": s2["segment_id"],
                        "source_text": s1["text"],
                        "target_text": s2["text"],
                        "source_page": None,
                        "target_page": None,
                        "source_section": s1.get("section", "Canonical Record"),
                        "target_section": s2.get("section", "Canonical Record"),
                        "strategy_used": "UniversalCrossCheckStrategy",
                        "strategy_confidence": self.confidence,
                        "entity_type": s1["metadata"].get("entity_type") or s2["metadata"].get("entity_type") or "Generic",
                        "metadata": {
                            "source_record_id": rec1_id,
                            "target_record_id": rec2_id,
                            "pairing_reason": reason,
                            "common_properties": list(common_keys)
                        }
                    })

        # 2. Generic Cross-Check between Documents across different files
        import uuid
        docs_by_id = {}
        for seg in doc_segs:
            doc_id = seg["metadata"].get("document_id")
            if doc_id:
                try:
                    uuid.UUID(str(doc_id))
                    docs_by_id.setdefault(str(doc_id), []).append(seg)
                except ValueError:
                    pass
            
        doc_ids = list(docs_by_id.keys())
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                id1 = doc_ids[i]
                id2 = doc_ids[j]
                
                segs1 = docs_by_id[id1][:3]
                segs2 = docs_by_id[id2][:3]
                
                for s1 in segs1:
                    for s2 in segs2:
                        pairs.append({
                            "source_document_id": id1,
                            "target_document_id": id2,
                            "source_segment_id": s1["segment_id"],
                            "target_segment_id": s2["segment_id"],
                            "source_text": s1["text"],
                            "target_text": s2["text"],
                            "source_page": s1.get("page"),
                            "target_page": s2.get("page"),
                            "source_section": s1.get("section"),
                            "target_section": s2.get("section"),
                            "strategy_used": "UniversalCrossCheckStrategy",
                            "strategy_confidence": self.confidence,
                            "entity_type": "DocumentCrossCheck",
                            "metadata": {
                                "source_document_id": id1,
                                "target_document_id": id2,
                                "pairing_reason": "Cross-File Document Comparison"
                            }
                        })

        return pairs

# Register concrete strategies inside StrategyRegistry dynamically
StrategyRegistry.register("SameVersionStrategy", SameVersionStrategy)
StrategyRegistry.register("SameEntityTypeStrategy", SameEntityTypeStrategy)
StrategyRegistry.register("SameDepartmentStrategy", SameDepartmentStrategy)
StrategyRegistry.register("SameTitleStrategy", SameTitleStrategy)
StrategyRegistry.register("SimilarityWindowStrategy", SimilarityWindowStrategy)
StrategyRegistry.register("UniversalCrossCheckStrategy", UniversalCrossCheckStrategy)

