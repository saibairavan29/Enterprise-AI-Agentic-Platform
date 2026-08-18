import re
from datetime import datetime
from ..exceptions.exceptions import EvidenceExtractionException

class EvidenceExtractor:
    """
    Decoupled evidence compiler extracting key differences, contradictions,
    timelines gap, and fields matching maps between candidate comparison pairs.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        # Load contradiction keywords from config or default lists
        self.contradiction_keywords = self.config.get(
            "contradiction_keywords", 
            ["not", "no", "except", "increased", "decreased", "higher", "lower", "changed", "adjusted"]
        )

    def extract_evidence(self, candidate, similarity_report: dict) -> dict:
        if not candidate:
            raise EvidenceExtractionException("Candidate input cannot be empty.")
            
        try:
            evidence_data = {
                "duplicate_fields": [],
                "contradiction_terms": [],
                "version_difference": 0,
                "numeric_difference": 0.0,
                "date_difference_days": 0.0
            }
            
            # 1. Inspect version timeline differences
            # Read version info from metadata properties
            cand_meta = candidate.metadata or {}
            src_ver = cand_meta.get("source_version")
            tgt_ver = cand_meta.get("target_version")
            
            if src_ver and tgt_ver:
                try:
                    v1 = int(str(src_ver).replace("ver-", ""))
                    v2 = int(str(tgt_ver).replace("ver-", ""))
                    evidence_data["version_difference"] = abs(v1 - v2)
                except ValueError:
                    pass
            
            # 2. Extract numeric differences (if present in metadata)
            if "difference" in cand_meta:
                evidence_data["numeric_difference"] = float(cand_meta["difference"])
                
            # 3. Identify matching contradiction keywords in text strings
            text1 = candidate.source_text.lower()
            text2 = candidate.target_text.lower()
            
            for term in self.contradiction_keywords:
                pattern = r'\b' + re.escape(term) + r'\b'
                # Checks if a term is present in one text but absent or matched differently in the other
                in1 = bool(re.search(pattern, text1))
                in2 = bool(re.search(pattern, text2))
                
                if in1 != in2:
                    # One text contains the term while the other does not (contradiction signal)
                    evidence_data["contradiction_terms"].append(term)
                    
            # 4. Check for duplicate keys
            # If comparing fields of records, check if canonical values match
            if candidate.strategy_used == "SameEntityTypeStrategy":
                # For record types, check matching keys inside text
                # (Simple text check or fields lookup)
                evidence_data["duplicate_fields"].append("entity_type")
                
            return evidence_data
            
        except Exception as e:
            raise EvidenceExtractionException(f"Failed to compile evidence: {str(e)}")
