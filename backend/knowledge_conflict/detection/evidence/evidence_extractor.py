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
                "property_differences": [],
                "version_difference": 0,
                "numeric_difference": 0.0,
                "date_difference_days": 0.0
            }
            
            # 1. Inspect version timeline differences
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
                in1 = bool(re.search(pattern, text1))
                in2 = bool(re.search(pattern, text2))
                
                if in1 != in2:
                    evidence_data["contradiction_terms"].append(term)

            # 4. Extract property key-value differences and timeline date conflicts
            def parse_kv(raw_text):
                kv = {}
                parts = raw_text.split("|")
                for p in parts:
                    if ":" in p:
                        k, v = p.split(":", 1)
                        kv[k.strip().lower()] = v.strip().lower()
                return kv

            kv1 = parse_kv(candidate.source_text)
            kv2 = parse_kv(candidate.target_text)

            date_keys = ["joining_date", "joining date", "date", "effective_date", "effective date", "created_at", "observation_date", "observation date", "due_date"]

            for k in set(kv1.keys()).intersection(set(kv2.keys())):
                if k not in ["entity type", "entity_type"] and kv1[k] != kv2[k]:
                    evidence_data["property_differences"].append(k)

                    # Check for timeline date sequence conflict
                    if any(dk in k for dk in date_keys):
                        d_match1 = re.search(r'\d{4}-\d{2}-\d{2}', kv1[k])
                        d_match2 = re.search(r'\d{4}-\d{2}-\d{2}', kv2[k])
                        if d_match1 and d_match2:
                            try:
                                dt1 = datetime.strptime(d_match1.group(0), "%Y-%m-%d")
                                dt2 = datetime.strptime(d_match2.group(0), "%Y-%m-%d")
                                gap = abs((dt2 - dt1).days)
                                evidence_data["date_difference_days"] = float(gap)
                                evidence_data["timeline_conflict"] = True
                                evidence_data["timeline_details"] = f"Date mismatch on '{k}': {d_match1.group(0)} vs {d_match2.group(0)} ({gap} days gap)"
                            except ValueError:
                                pass

            # 5. Check for duplicate keys
            if candidate.strategy_used in ["SameEntityTypeStrategy", "UniversalCrossCheckStrategy"]:
                evidence_data["duplicate_fields"].append("entity_type")
                
            return evidence_data
            
        except Exception as e:
            raise EvidenceExtractionException(f"Failed to compile evidence: {str(e)}")
