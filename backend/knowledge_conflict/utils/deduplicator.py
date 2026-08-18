import hashlib
import logging

logger = logging.getLogger('enterprise')

class CandidateDeduplicator:
    """
    Utility class that deduplicates list of candidate pairs based on a deterministic hash.
    Enforces uniqueness across bidirectional combinations (e.g. A->B is equivalent to B->A).
    """
    @staticmethod
    def generate_fingerprint(doc1: str, seg1: str, doc2: str, seg2: str, strategy: str) -> str:
        """
        Creates a stable SHA-256 fingerprint for a pair of segments.
        Sorts the identifiers to ensure bidirectional pairs result in the same hash.
        """
        # Sort documents and segments to make order independent
        sorted_docs = sorted([str(doc1), str(doc2)])
        sorted_segs = sorted([str(seg1), str(seg2)])
        
        raw_key = f"{sorted_docs[0]}:{sorted_segs[0]}||{sorted_docs[1]}:{sorted_segs[1]}||{strategy}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    @classmethod
    def deduplicate(cls, candidates: list) -> tuple:
        """
        Filters out duplicate candidate pairs from the list.
        If duplicates exist, retains the one with the highest strategy confidence.
        Returns a tuple: (deduplicated_list, duplicate_count)
        """
        unique_map = {}
        duplicates_removed = 0
        
        for cand in candidates:
            doc1 = cand["source_document_id"]
            seg1 = cand["source_segment_id"]
            doc2 = cand["target_document_id"]
            seg2 = cand["target_segment_id"]
            strat = cand["strategy_used"]
            conf = cand["strategy_confidence"]
            
            fingerprint = cls.generate_fingerprint(doc1, seg1, doc2, seg2, strat)
            cand["candidate_hash"] = fingerprint
            
            if fingerprint in unique_map:
                duplicates_removed += 1
                # Overwrite only if the new candidate has higher confidence
                if conf > unique_map[fingerprint]["strategy_confidence"]:
                    unique_map[fingerprint] = cand
            else:
                unique_map[fingerprint] = cand
                
        return list(unique_map.values()), duplicates_removed
