import os
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
            src_doc = candidate.source_document
            tgt_doc = candidate.target_document
            src_title = src_doc.title if src_doc else "Source File"
            tgt_title = tgt_doc.title if tgt_doc else "Target File"
            
            src_ext = os.path.splitext(src_title)[1].lower().strip('.') or "txt"
            tgt_ext = os.path.splitext(tgt_title)[1].lower().strip('.') or "txt"

            # Formulate file-type-aware provenance for Source A and Source B
            cand_meta = candidate.metadata or {}

            def clean_location(doc_title, ext, segment_id, page, section, record_key):
                ext_clean = ext.lower().strip('.')
                rec_id = cand_meta.get(record_key)
                
                clean_id = str(rec_id or segment_id or "").replace("rec-", "").replace("-full", "").replace("-content", "")
                
                if ext_clean in ['xlsx', 'xls', 'csv'] or "rec-" in str(segment_id).lower() or rec_id:
                    sheet_name = cand_meta.get("sheet_name") or (section if section and "Worksheet" in str(section) else "Sheet1")
                    row_label = f"Row #{clean_id}" if clean_id and clean_id.isdigit() else (f"Row ({clean_id})" if clean_id else "Table Row")
                    return f"{doc_title} → Sheet: {sheet_name}, {row_label}"
                elif ext_clean == 'pdf':
                    pg = page or cand_meta.get("page") or 1
                    sec = section or cand_meta.get("section") or "General"
                    return f"{doc_title} → Page #{pg}, Section: {sec}"
                elif ext_clean in ['docx', 'doc', 'txt', 'md']:
                    sec = section or cand_meta.get("section") or "Main Content"
                    pg = page or cand_meta.get("page")
                    pg_str = f"Page #{pg}, " if pg else ""
                    return f"{doc_title} → {pg_str}Section: {sec}"
                elif ext_clean == 'json':
                    path_str = section or segment_id or "root"
                    return f"{doc_title} → JSON Node: {path_str}"
                else:
                    return f"{doc_title} → Location: {section or segment_id or 'General'}"

            src_loc_str = clean_location(src_title, src_ext, candidate.source_segment_id, candidate.source_page, candidate.source_section, "source_record_id")
            tgt_loc_str = clean_location(tgt_title, tgt_ext, candidate.target_segment_id, candidate.target_page, candidate.target_section, "target_record_id")

            src_prov = {"file": src_title, "type": src_ext.upper(), "location_str": src_loc_str}
            tgt_prov = {"file": tgt_title, "type": tgt_ext.upper(), "location_str": tgt_loc_str}

            # Check for version / revision files
            is_version_update = False
            version_change_summary = ""
            if "version" in candidate.strategy_used.lower() or "revision" in src_title.lower() or "revision" in tgt_title.lower() or "update" in src_title.lower() or "update" in tgt_title.lower():
                is_version_update = True
                version_change_summary = f"File Revision / Update Detected between '{src_title}' and '{tgt_title}'."

            evidence_data = {
                "duplicate_fields": [],
                "contradiction_terms": [],
                "property_differences": [],
                "conflicting_facts": [],
                "variance_points": [],
                "matched_facts": [],
                "version_difference": 0,
                "is_version_update": is_version_update,
                "version_change_summary": version_change_summary,
                "numeric_difference": 0.0,
                "date_difference_days": 0.0,
                "source_provenance": src_prov,
                "target_provenance": tgt_prov,
                "match_scope": "Full Content",
                "matched_count": 0,
                "total_count": 0,
                "what_fact": "Identical Content",
                "why_explanation": "",
                "source_a_details": {
                    "file": src_title,
                    "location": src_prov["location_str"],
                    "text": candidate.source_text
                },
                "source_b_details": {
                    "file": tgt_title,
                    "location": tgt_prov["location_str"],
                    "text": candidate.target_text
                }
            }
            
            # 1. Inspect version timeline differences
            src_ver = cand_meta.get("source_version")
            tgt_ver = cand_meta.get("target_version")
            
            if src_ver and tgt_ver:
                try:
                    v1 = int(str(src_ver).replace("ver-", ""))
                    v2 = int(str(tgt_ver).replace("ver-", ""))
                    evidence_data["version_difference"] = abs(v1 - v2)
                    evidence_data["is_version_update"] = True
                    evidence_data["version_change_summary"] = f"Document Version Revision: v{v1} vs v{v2}."
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

            # 4. Extract property key-value differences and normalized fact comparisons
            def parse_kv(raw_text):
                kv = {}
                parts = raw_text.split("|")
                for p in parts:
                    if ":" in p:
                        k, v = p.split(":", 1)
                        clean_k = k.strip().lower()
                        clean_v = v.strip()
                        # Ignore unpopulated placeholder values when evaluating factual consistency
                        if clean_v and clean_v.lower() not in ["none", "n/a", "null", "nan", "undefined", "-"]:
                            kv[clean_k] = clean_v
                return kv

            def normalize_val(val_str):
                clean = str(val_str).strip().lower()
                clean = clean.replace('₹', '').replace('$', '').replace(',', '')
                return clean

            kv1 = parse_kv(candidate.source_text)
            kv2 = parse_kv(candidate.target_text)

            date_keys = ["joining_date", "joining date", "date", "effective_date", "effective date", "created_at", "observation_date", "observation date", "due_date"]

            matched_count = 0
            conflicting_facts = []
            variance_points = []

            for k in set(kv1.keys()).intersection(set(kv2.keys())):
                if k in ["entity type", "entity_type"]:
                    continue
                
                v1_norm = normalize_val(kv1[k])
                v2_norm = normalize_val(kv2[k])

                if v1_norm == v2_norm:
                    matched_count += 1
                    evidence_data["matched_facts"].append(k)
                else:
                    evidence_data["property_differences"].append(k)
                    fact_label = k.replace('_', ' ').title()
                    conflicting_facts.append({
                        "fact_name": fact_label,
                        "source_a_value": kv1[k],
                        "source_b_value": kv2[k],
                        "difference": f"Source A: '{kv1[k]}' vs Source B: '{kv2[k]}'"
                    })
                    variance_points.append({
                        "point_name": fact_label,
                        "source_a_file": src_title,
                        "source_a_location": src_prov["location_str"],
                        "source_a_value": kv1[k],
                        "source_b_file": tgt_title,
                        "source_b_location": tgt_prov["location_str"],
                        "source_b_value": kv2[k],
                        "variance_type": "Factual Discrepancy" if not is_version_update else "Updated Version Change",
                        "impact_note": f"Value differs on '{fact_label}': '{kv1[k]}' vs '{kv2[k]}'"
                    })

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

            # If no key-value pairs were found (e.g. for unstructured document, policy, or OCR text segments), compare raw text strings directly
            if not kv1 and not kv2 and candidate.source_text and candidate.target_text:
                s_clean = candidate.source_text.strip()
                t_clean = candidate.target_text.strip()
                if s_clean.lower() != t_clean.lower():
                    evidence_data["property_differences"].append("Document Content")
                    fact_label = "Document Content / Policy Rule"
                    conflicting_facts.append({
                        "fact_name": fact_label,
                        "source_a_value": s_clean,
                        "source_b_value": t_clean,
                        "difference": f"Source A: '{s_clean}' vs Source B: '{t_clean}'"
                    })
                    variance_points.append({
                        "point_name": fact_label,
                        "source_a_file": src_title,
                        "source_a_location": src_prov["location_str"],
                        "source_a_value": s_clean,
                        "source_b_file": tgt_title,
                        "source_b_location": tgt_prov["location_str"],
                        "source_b_value": t_clean,
                        "variance_type": "Policy / Content Variance" if not is_version_update else "Revision Policy Update",
                        "impact_note": "Text segment content varies between compared files."
                    })

            evidence_data["conflicting_facts"] = conflicting_facts
            evidence_data["variance_points"] = variance_points
            evidence_data["matched_count"] = matched_count
            total_facts = matched_count + len(conflicting_facts)
            evidence_data["total_count"] = total_facts

            if total_facts > 0 and (kv1 or kv2):
                match_pct = round((matched_count / float(total_facts)) * 100.0, 1)
                evidence_data["match_scope"] = f"{matched_count}/{total_facts} Attributes ({match_pct}%)"
            else:
                evidence_data["match_scope"] = "Full Text Segment"

            # Formulate Similarity Evidence Explanation (WHAT, WHERE, DIFFERENCES, WHY)
            if len(conflicting_facts) == 0:
                evidence_data["what_fact"] = "Identical Content"
                evidence_data["why_explanation"] = f"Both files contain effectively identical content across {matched_count or 'all'} comparable attributes."
            else:
                if kv1 or kv2:
                    matched_names = [m.replace('_', ' ').title() for m in evidence_data["matched_facts"][:3]]
                    diff_names = [c["fact_name"] for c in conflicting_facts[:3]]
                    matched_str = ", ".join(matched_names) if matched_names else "overall structure"
                    diff_str = ", ".join(diff_names) if diff_names else "specific values"

                    evidence_data["what_fact"] = f"{matched_count} Matched / {len(conflicting_facts)} Differing Attributes"
                    evidence_data["why_explanation"] = f"Both sources share comparable information. Matching attributes: [{matched_str}]. Differing attributes: [{diff_str}]."
                else:
                    evidence_data["what_fact"] = "Material Content Difference"
                    evidence_data["why_explanation"] = f"Material difference detected between compared document segments."

                primary_diff = conflicting_facts[0]
                evidence_data["source_a_details"]["value"] = primary_diff["source_a_value"]
                evidence_data["source_b_details"]["value"] = primary_diff["source_b_value"]

            # Check for duplicate keys
            if candidate.strategy_used in ["SameEntityTypeStrategy", "UniversalCrossCheckStrategy"]:
                evidence_data["duplicate_fields"].append("entity_type")
                
            return evidence_data
            
        except Exception as e:
            raise EvidenceExtractionException(f"Failed to compile evidence: {str(e)}")
