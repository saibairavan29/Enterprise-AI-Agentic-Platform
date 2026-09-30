import hashlib
import logging

logger = logging.getLogger('enterprise')

class CandidateDeduplicator:
    """
    Utility class that deduplicates list of candidate pairs based on a deterministic hash.
    Enforces uniqueness across bidirectional combinations (e.g. A->B is equivalent to B->A)
    and eliminates text-level duplicates across nested sentence/paragraph segment boundaries.
    """
    @staticmethod
    def generate_fingerprint(doc1: str, text1: str, doc2: str, text2: str, strategy: str = "") -> str:
        """
        Creates a stable SHA-256 fingerprint for a pair of document texts.
        Sorts document IDs and normalized text contents to ensure bidirectional and
        text-equivalent segment pairs result in the exact same hash.
        """
        sorted_docs = sorted([str(doc1), str(doc2)])
        
        # Punctuation, boilerplate & whitespace normalization for text comparison
        import re
        def clean_txt(t):
            if not t:
                return ""
            c = re.sub(r'ocr\s+test\s+note:.*$', '', t, flags=re.IGNORECASE | re.DOTALL)
            c = re.sub(r'\s+', ' ', c).strip().lower()
            return c[:250]

        t1 = clean_txt(text1)
        t2 = clean_txt(text2)
        sorted_texts = sorted([t1, t2])
        
        raw_key = f"{sorted_docs[0]}||{sorted_docs[1]}||{sorted_texts[0]}||{sorted_texts[1]}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    @classmethod
    def deduplicate(cls, candidates: list) -> tuple:
        """
        Filters out duplicate candidate pairs from the list based on document IDs and text contents.
        If duplicates exist, retains the one with the highest strategy confidence.
        Returns a tuple: (deduplicated_list, duplicate_count)
        """
        unique_map = {}
        duplicates_removed = 0
        
        for cand in candidates:
            doc1 = cand.get("source_document_id", "")
            doc2 = cand.get("target_document_id", "")
            text1 = cand.get("source_text") or cand.get("source_segment_id", "")
            text2 = cand.get("target_text") or cand.get("target_segment_id", "")
            strat = cand.get("strategy_used", "")
            conf = cand.get("strategy_confidence", 0.0)
            
            fingerprint = cls.generate_fingerprint(doc1, text1, doc2, text2, strat)
            cand["candidate_hash"] = fingerprint
            
            if fingerprint in unique_map:
                duplicates_removed += 1
                # Overwrite only if the new candidate has higher confidence
                if conf > unique_map[fingerprint]["strategy_confidence"]:
                    unique_map[fingerprint] = cand
            else:
                unique_map[fingerprint] = cand
                
        return list(unique_map.values()), duplicates_removed
