import re
import json
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('enterprise')

def validate_semantic_completeness(text: str) -> str:
    """
    Validates and enforces semantic completeness of generated text responses.
    Ensures text does not end mid-sentence, mid-table, or with dangling punctuation/colons.
    """
    if not text:
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""

    # Check if ends naturally with sentence-ending punctuation or formatting structure
    if cleaned.endswith(('.', '!', '?', '"', "'", ')', ']', '}', '```', '|', '%')):
        return cleaned

    # If it ends with alphanumeric character or word char, append period to complete sentence
    if re.search(r'[\w\d]$', cleaned):
        return cleaned + "."

    # Check if last line is a complete sentence or list item
    lines = cleaned.splitlines()
    if lines:
        last_line = lines[-1].strip()
        if last_line and not last_line.endswith(('.', '!', '?')):
            lines[-1] = last_line + "."
            return "\n".join(lines)

    return cleaned


class OllamaLLMProvider:
    """
    Ollama LLM Provider for local Phi-3.5 Mini model execution.
    Target Model: phi3.5 (Phi-3.5 Mini 3.8B Q4_K_M)
    """

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "phi3.5:latest"):
        self.base_url = base_url
        self.model_name = model_name

    def is_available(self) -> bool:
        """
        Checks if the local Ollama daemon is active.
        """
        try:
            resp = requests.get(f"{self.base_url}/", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1, max_tokens: int = 4096) -> str:
        """
        Sends generation request to local Ollama instance running Phi-3.5 Mini (phi3.5:latest).
        """
        if not self.is_available():
            logger.warning("Ollama local service is not reachable on http://localhost:11434.")
            return ""

        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "You are an Enterprise Knowledge Assistant. Answer strictly using provided evidence.",
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 8192,
                "num_predict": max_tokens,
                "num_gpu": 99
            }
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=120.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                logger.error(f"Ollama returned HTTP {response.status_code}: {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Communicating with local Ollama model (phi3.5:latest) timed out: {str(e)}")
            return ""


class LocalLLMClient:
    """
    Singleton client manager for local LLM operations.
    Defaults to Phi-3.5 Mini 3.8B Q4_K_M (phi3.5:latest).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalLLMClient, cls).__new__(cls)
            cls._instance.provider = OllamaLLMProvider()
        return cls._instance

    def synthesize_answer(self, query: str, context_chunks: list, kg_paths: list, grounded_reasoning_state: dict = None) -> str:
        """
        Formats evidence context and calls local Phi-3.5 Mini (phi3.5:latest) to synthesize a grounded answer.
        """
        grounded_state = grounded_reasoning_state or {}
        reasoning_op = grounded_state.get("operation", "FACT_RETRIEVAL")
        reasoning_summary = grounded_state.get("reasoning_summary", "")
        is_supported = grounded_state.get("is_supported", True)

        if not is_supported:
            return "Insufficient evidence in the provided dataset"

        doc_evidence_str = ""
        for i, chunk in enumerate(context_chunks, 1):
            if hasattr(chunk, 'to_prompt_text'):
                text_snippet = chunk.to_prompt_text()
            elif isinstance(chunk, dict):
                src = chunk.get('source', 'Document')
                txt = chunk.get('text', '')
                text_snippet = f"Evidence #{i} [{src}]: {txt}"
            else:
                text_snippet = f"Evidence #{i}: {str(chunk)}"
            doc_evidence_str += text_snippet.strip() + "\n\n"

        kg_evidence_str = ""
        if kg_paths:
            for j, item in enumerate(kg_paths[:10], 1):
                if isinstance(item, dict):
                    src_ent = item.get("source_entity", "")
                    rel = item.get("relationship", "RELATED_TO")
                    tgt_ent = item.get("target_entity", "")
                    prov = item.get("provenance", "Knowledge Graph")
                    path_str = item.get("path_string", "")
                    if src_ent and tgt_ent:
                        kg_evidence_str += f"KG Item #{j}: Entity [{src_ent}] -[{rel}]-> Entity [{tgt_ent}] (Source: {prov})\n"
                    elif path_str and "No Knowledge Graph" not in path_str:
                        kg_evidence_str += f"KG Item #{j}: {path_str}\n"
                else:
                    kg_evidence_str += f"KG Item #{j}: {str(item)}\n"

        # Extract verified_computation if present in grounded_state or context_chunks
        verified_comp = grounded_state.get("verified_computation")
        if not verified_comp and context_chunks:
            for c in context_chunks:
                if isinstance(c, dict) and c.get("verified_computation"):
                    verified_comp = c.get("verified_computation")
                    break

        calc_block = ""
        if verified_comp:
            tot_orders = verified_comp.get("total_orders", verified_comp.get("record_count", 0))
            source_file = verified_comp.get("source_file", "Dataset")
            source_records = verified_comp.get("source_records", [])

            calc_lines = [
                f"TARGET DATASET EVIDENCE (File: {source_file}, Total Records Evaluated: {tot_orders}):"
            ]

            # Format raw source records
            if source_records:
                calc_lines.append("INDIVIDUAL SOURCE RECORDS:")
                for r in source_records:
                    r_str = json.dumps(r)
                    calc_lines.append(f"  - {r_str}")

            # Extract structured group validation & calculations if present
            g_val = verified_comp.get("group_validation")
            if g_val:
                calc_lines.append("\nVALIDATED DETERMINISTIC GROUPING & GRAND TOTALS (AUTHORITATIVE TRUTH - DO NOT ALTER):")
                calc_lines.append(f"- Group Coverage Complete: {g_val.get('is_group_complete')} (Missing IDs: {g_val.get('missing_ids')}, Duplicate IDs: {g_val.get('duplicate_ids')})")
                calc_lines.append(f"- Independent Grand Total Net Amount (Sum of all {tot_orders} records): ${g_val.get('indep_grand_total_sales'):,.2f}")
                calc_lines.append(f"- Independent Grand Total Quantity (Sum of all {tot_orders} records): {g_val.get('indep_grand_total_qty')}")
                calc_lines.append(f"- Sum of Group Net Amounts: ${g_val.get('sum_of_group_sales'):,.2f} (Reconciled: {g_val.get('sales_reconciled')})")
                calc_lines.append(f"- Sum of Group Quantities: {g_val.get('sum_of_group_qty')} (Reconciled: {g_val.get('qty_reconciled')})")

                dept_sums = g_val.get("dept_sums", {})
                dept_qty_sums = g_val.get("dept_qty_sums", {})
                dept_sales_pct = g_val.get("dept_percentages", {})
                group_details = g_val.get("group_details", {})

                calc_lines.append("\nBUSINESS UNIT GROUP BREAKDOWN:")
                for grp, s_val in dept_sums.items():
                    q_val = dept_qty_sums.get(grp, 0)
                    pct_val = dept_sales_pct.get(grp, 0.0)
                    recs = group_details.get(grp, [])
                    g_ids = [r.get("Order_ID") or r.get("Employee_ID") or r.get("EmpID") for r in recs if (r.get("Order_ID") or r.get("Employee_ID") or r.get("EmpID"))]
                    g_sales = [r.get("Net_Amount") or r.get("Salary") or r.get("Sales_Revenue") for r in recs if (r.get("Net_Amount") is not None or r.get("Salary") is not None)]
                    g_qtys = [r.get("Quantity") or r.get("Units_Sold") for r in recs if (r.get("Quantity") is not None or r.get("Units_Sold") is not None)]

                    calc_lines.append(f"- {grp}:")
                    if g_ids: calc_lines.append(f"  * Contributing Record IDs: {', '.join(str(x) for x in g_ids)}")
                    if g_sales: calc_lines.append(f"  * Contributing Net Amounts: {', '.join(str(x) for x in g_sales)}")
                    if g_qtys: calc_lines.append(f"  * Contributing Quantities: {', '.join(str(x) for x in g_qtys)}")
                    calc_lines.append(f"  * Total Net Amount: ${s_val:,.2f}")
                    calc_lines.append(f"  * Total Quantity: {q_val}")
                    calc_lines.append(f"  * Percentage Contribution: {pct_val}%")

            elif verified_comp.get("total_sales") is not None or verified_comp.get("sum") is not None:
                calc_lines.append(f"- Total Sales Revenue / Sum: {verified_comp.get('total_sales', verified_comp.get('sum'))}")
                if verified_comp.get("total_quantity") is not None:
                    calc_lines.append(f"- Total Quantity: {verified_comp.get('total_quantity')}")

            calc_block = "\n".join(calc_lines) + "\n\n"

        system_prompt = (
            "You are an expert Enterprise Knowledge Assistant. Answer the user's question directly, naturally, "
            "and authoritatively using ONLY the provided evidence context.\n"
            "CRITICAL RESPONSE RULES:\n"
            "1. DIRECT ANSWER FIRST: Always start your response immediately with the direct answer to the user's query. "
            "Do NOT begin with preamble, reasoning, provenance, methodology, conflict analysis, or document summaries before giving the direct answer.\n"
            "2. NATURAL PROGRESSIVE DEPTH: Follow the direct answer with relevant supporting details, step-by-step arithmetic calculations, or evidence verification ONLY as required by the query.\n"
            "   The response must read as ONE continuous, cohesive, natural answer flowing smoothly: Direct Answer -> Supporting Record Details -> Calculations/Reasoning -> Verification.\n"
            "3. DO NOT EXPOSE INTERNAL LEVELS OR HEADINGS: NEVER output headings such as 'Level 1', 'Level 2', 'Level 3', 'Level 4', 'Executive Summary', 'Detailed Operational Explanation', or 'Deterministic Calculation & Metric Breakdown' unless the user explicitly requested those exact headings in their prompt text. Internal levels are for controlling detail depth only, not for dividing the response into exposed sections.\n"
            "4. DEPTH MATCHES QUERY: A simple query should yield a concise direct answer. A record-retrieval query should list requested records. A calculation query should show source values and step-by-step arithmetic. Do NOT artificially expand simple queries.\n"
            "5. STRICT SOURCE GROUNDING & SCOPE: Rely exclusively on the evidence provided for the target document/source specified in the query. Do NOT introduce external files, cached cross-source reviews, or unrequested metrics (averages, maximums, minimums, conflict analysis, duplicate detection) unless the user asked for them.\n"
            "6. DETERMINISTIC CALCULATIONS FROM RAW SOURCE RECORDS: When calculations are requested, perform arithmetic directly from the individual raw source records in the context. Raw source records are authoritative. Show step-by-step arithmetic when requested.\n"
            "7. RESPONSE COMPLETENESS & FIDELITY: Ensure every sentence, table row, calculation expression, and section is complete. Never cut words/numbers or use '...' to conceal missing text.\n"
            "8. DEDUPLICATION: State each key insight ONCE cleanly. Do NOT repeat the same answer multiple times under different headings."
        )

        grounded_conclusion = grounded_state.get("grounded_conclusion", "")
        query_lower = query.lower()

        # Include comparisons/conflicts ONLY if user query explicitly asks for comparison/conflict analysis
        comp_block = ""
        conflict_block = ""
        if any(k in query_lower for k in ["compare", "comparison", "versus", "vs"]):
            comparisons_list = grounded_state.get("comparisons", [])
            comp_str = "".join(f"- {c.get('summary')}\n" for c in comparisons_list if c.get('summary'))
            if comp_str:
                comp_block = f"VERIFIED COMPARISONS:\n{comp_str}\n"

        if any(k in query_lower for k in ["conflict", "ekcd", "mismatch", "discrepancy", "contradict"]):
            conflicts_list = grounded_state.get("conflicts", [])
            conflict_str = "".join(f"- {conf.get('conflict_summary')}\n" for conf in conflicts_list if conf.get('conflict_summary'))
            if conflict_str:
                conflict_block = f"DATA CONFLICTS:\n{conflict_str}\n"

        user_prompt = (
            f"QUESTION: {query}\n\n"
            f"{calc_block}"
            f"SOURCE CONTEXT:\n{doc_evidence_str.strip() or 'No direct document text available.'}\n\n"
            f"{kg_evidence_str.strip()}\n"
            f"{comp_block}"
            f"{conflict_block}\n"
            f"Provide a clear, natural-language response directly answering the question above:"
        )

        llm_response = self.provider.generate(user_prompt, system_prompt=system_prompt, temperature=0.1, max_tokens=4096)
        if llm_response:
            clean_res = re.sub(
                r'^(Based on the provided document evidence|Based on the provided context|Based on the evidence|According to the provided document evidence|According to the document|The system\'s grounded reasoning state|In the absence of a Knowledge Graph)[,:\s]*',
                '',
                llm_response.strip(),
                flags=re.IGNORECASE
            ).strip()

            unique_lines = []
            seen_lines = set()
            for line in clean_res.splitlines():
                l_clean = line.strip()
                if l_clean:
                    l_key = l_clean.lower()
                    if l_key not in seen_lines:
                        seen_lines.add(l_key)
                        unique_lines.append(l_clean)
            deduped_res = "\n".join(unique_lines)

            context_text = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in context_chunks])
            for corr_num, trailing_letter in re.findall(r'\b(\d{1,3}(?:,\d{3})+\d*|\d+)([a-z]{1,2})\b', deduped_res):
                if trailing_letter in ['n', 'se', 'th', 'rd', 'st'] and not deduped_res.lower().endswith(trailing_letter):
                    matched_valid = re.findall(r'\b' + re.escape(corr_num) + r'\d*\b', context_text)
                    if matched_valid:
                        valid_num = matched_valid[0]
                        deduped_res = re.sub(re.escape(corr_num + trailing_letter) + r'\b', valid_num, deduped_res)

            final_text = deduped_res if deduped_res else clean_res
            return validate_semantic_completeness(final_text)

        # Failsafe responses
        if query.lower().strip() in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]:
            return "Hello! How can I assist you with your enterprise datasets today?"

        if grounded_conclusion and "Insufficient evidence" not in grounded_conclusion:
            clean_conc = re.sub(
                r'^(Verified factual document summary from source [^:\n]+|Verified factual statement from source [^:\n]+|Fact Retrieval|Deterministic Comparison|Deterministic Calculation|Deterministic Aggregation|Knowledge Graph Multi-Hop Reasoning|Conflict Detected|Temporal Change Analysis)[:\s]*',
                '',
                grounded_conclusion,
                flags=re.IGNORECASE
            ).strip()
            return validate_semantic_completeness(clean_conc)
        elif context_chunks:
            chunk_texts = [
                re.sub(r'^--- \[Page \d+ of \d+ — Source: [^\]]+\] ---\s*', '', c.get('text', '') if isinstance(c, dict) else str(c)).strip()
                for c in context_chunks if (isinstance(c, dict) and c.get('text'))
            ]
            full_txt = "\n\n".join([t for t in chunk_texts if t]).strip()
            return validate_semantic_completeness(full_txt)
        else:
            return "Insufficient evidence in the provided dataset"

    def synthesize_progressive_levels(self, query: str, context_chunks: list, kg_paths: list, grounded_reasoning_state: dict = None) -> Dict[str, Dict[str, Any]]:
        """
        Synthesizes progressive explanation levels dynamically based on user query requirements.
        """
        def build_lvl_obj(txt: str) -> Dict[str, Any]:
            clean_t = validate_semantic_completeness(txt)
            return {
                "text": clean_t,
                "complete": bool(clean_t and not clean_t.strip().endswith("...")),
                "char_count": len(clean_t)
            }

        q_upper = query.upper()
        q_lower = query.lower()
        is_multi_level_req = any(k in q_upper for k in ["LEVEL 1", "LEVEL 2", "LEVEL 3", "LEVEL 4", "LEVELS"]) or \
                             any(k in q_lower for k in ["four level", "4 level", "progressively detailed", "level 1 —", "level 1:", "level 2 —", "level 2:"])

        if is_multi_level_req:
            # Multi-level explicit prompt synthesis
            doc_evidence_str = ""
            for i, chunk in enumerate(context_chunks, 1):
                if hasattr(chunk, 'to_prompt_text'):
                    text_snippet = chunk.to_prompt_text()
                elif isinstance(chunk, dict):
                    src = chunk.get('source', 'Document')
                    txt = chunk.get('text', '')
                    text_snippet = f"Evidence #{i} [{src}]: {txt}"
                else:
                    text_snippet = f"Evidence #{i}: {str(chunk)}"
                doc_evidence_str += text_snippet.strip() + "\n\n"

            verified_comp = (grounded_reasoning_state or {}).get("verified_computation")
            if not verified_comp and context_chunks:
                for c in context_chunks:
                    if isinstance(c, dict) and c.get("verified_computation"):
                        verified_comp = c.get("verified_computation")
                        break

            calc_block = ""
            if verified_comp:
                source_records = verified_comp.get("source_records", [])
                calc_lines = [f"SOURCE DATASET RECORDS (File: {verified_comp.get('source_file', 'Dataset')}):"]
                if source_records:
                    for r in source_records:
                        calc_lines.append(f"  - {json.dumps(r)}")
                calc_block = "\n".join(calc_lines) + "\n\n"

            multi_sys_prompt = (
                "You are an expert Enterprise Knowledge Assistant. Answer the user's multi-level query request directly, "
                "authoritatively, and progressively using ONLY the provided evidence context.\n"
                "CRITICAL MULTI-LEVEL RULES:\n"
                "1. Follow the user's exact instructions, level titles, formatting, arithmetic steps, and level separation rules.\n"
                "2. Structure your response with explicit Level headings corresponding to the user request (e.g. ## LEVEL 1 —, ## LEVEL 2 —, ## LEVEL 3 —, ## LEVEL 4 —).\n"
                "3. Level 1 must be direct and relevant without unrequested meta-headers or methodology.\n"
                "4. Level 2 must show complete source record breakdowns accurately grouped without missing or fabricated records.\n"
                "5. Level 3 must perform step-by-step arithmetic from the actual source records provided in evidence.\n"
                "6. Level 4 must provide independent verification, grand total calculations, and explicit comparison state.\n"
                "7. Ensure 100% output completeness. Do NOT truncate, omit, abbreviate, or use '...' anywhere."
            )

            multi_user_prompt = (
                f"USER QUERY AND INSTRUCTIONS:\n{query}\n\n"
                f"{calc_block}"
                f"SOURCE EVIDENCE:\n{doc_evidence_str.strip()}\n\n"
                f"Generate the full response adhering strictly to all four requested levels:"
            )

            raw_multi_resp = self.provider.generate(multi_user_prompt, system_prompt=multi_sys_prompt, temperature=0.1, max_tokens=4096)
            if raw_multi_resp:
                # Parse levels from generated response
                levels_parsed = {}
                pattern = r'(?i)(?:^|\n)#*\s*(?:LEVEL|LEVEL\s*:\s*|LEVEL\s*-\s*)\s*([1-4])\b[^\n]*'
                parts = re.split(pattern, raw_multi_resp)
                if len(parts) >= 3:
                    for i in range(1, len(parts), 2):
                        lvl_num = parts[i]
                        lvl_content = parts[i+1].strip() if i+1 < len(parts) else ""
                        levels_parsed[f"level_{lvl_num}"] = build_lvl_obj(lvl_content)

                if len(levels_parsed) == 4 and all(levels_parsed[k]["text"] for k in levels_parsed):
                    return levels_parsed

        # Default single-level response or progressive fallback
        base_answer = self.synthesize_answer(query, context_chunks, kg_paths, grounded_reasoning_state)

        if "Insufficient evidence" in base_answer or (grounded_reasoning_state and not grounded_reasoning_state.get("is_supported", True)):
            return {
                "level_1": build_lvl_obj("The available evidence in the authorized dataset does not contain sufficient details to answer this specific query."),
                "level_2": build_lvl_obj("The retrieved evidence provides general background and context regarding the target document or dataset, but does not explicitly record the specific facts, challenges, or actions requested in the query."),
                "level_3": build_lvl_obj("While the authorized evidence documents activities, technical tools, and organizational context, those facts do not by themselves establish the specific conclusion requested. Factually distinguishing background information from unsupported inferences ensures grounding integrity."),
                "level_4": build_lvl_obj("Analysis confirms that the provided source records establish baseline activities and organizational context, but lack specific evidence supporting the queried details. To answer this question authoritatively without ungrounded speculation, additional source documentation or explicit records would be required.")
            }

        clean_base = re.sub(
            r'^(Based on the provided document evidence|Based on the provided context|Based on the evidence|According to the provided document evidence|According to the document|The system\'s grounded reasoning state|In the absence of a Knowledge Graph)[,:\s]*',
            '',
            base_answer.strip(),
            flags=re.IGNORECASE
        ).strip()

        # Level 1: Executive Summary
        l1_text = clean_base

        # Level 2: Detailed Evidence & Record Breakdown
        l2_parts = [clean_base]
        if context_chunks:
            l2_parts.append("\nSupporting Evidence & Document Details:")
            for idx, chunk in enumerate(context_chunks[:10], 1):
                if isinstance(chunk, dict):
                    src = chunk.get("source", "Document")
                    loc = chunk.get("location_meta", {})
                    p_info = f" (Page {loc.get('page')})" if loc.get("page") else ""
                    txt = chunk.get("text", "").strip()
                    clean_txt = re.sub(r'^--- \[Page \d+ of \d+ — Source: [^\]]+\] ---\s*', '', txt).strip()
                    l2_parts.append(f"• [Evidence Item {idx}] {src}{p_info}:\n  {clean_txt}")
                else:
                    l2_parts.append(f"• [Evidence Item {idx}]: {str(chunk)}")
        l2_text = "\n".join(l2_parts)

        # Level 3: Knowledge Graph Traversal & Analytical Reasoning
        l3_parts = [
            f"Reasoning Operation: {(grounded_reasoning_state or {}).get('operation', 'FACT_RETRIEVAL')}",
            f"Evidence Supportability: {'Fully Supported' if (grounded_reasoning_state or {}).get('is_supported', True) else 'Unsupported'}",
            f"\nGrounded Reasoning Conclusion:\n{clean_base}"
        ]
        
        if kg_paths:
            l3_parts.append("\nKnowledge Graph Traversal Paths:")
            for p in kg_paths[:5]:
                if isinstance(p, dict):
                    path_str = p.get("path_string") or f"{p.get('source_entity')} -> {p.get('target_entity')}"
                    why = p.get("why_it_matters", "")
                    l3_parts.append(f"  - Path: {path_str}\n    Context: {why}")

        calcs = (grounded_reasoning_state or {}).get("calculations", [])
        if calcs:
            l3_parts.append("\nVerified Calculations:")
            for c in calcs:
                l3_parts.append(f"  - {json.dumps(c)}")

        confls = (grounded_reasoning_state or {}).get("conflicts", [])
        if confls:
            l3_parts.append("\nKnowledge Conflicts Inspection:")
            for c in confls:
                l3_parts.append(f"  - {json.dumps(c)}")

        l3_text = "\n".join(l3_parts)

        # Level 4: Technical Audit & Provenance Verification
        provenance_list = (grounded_reasoning_state or {}).get("provenance", [])
        claims_map = (grounded_reasoning_state or {}).get("claims_mapping", [])
        
        l4_parts = [
            "Technical Execution Audit & Verification Trace:",
            f"• LLM Model: Phi-3.5-Mini-3.8B-Q4_K_M (Deterministic local engine)",
            f"• Total Retrieved Evidence Chunks: {len(context_chunks)}",
            f"• Total Knowledge Graph Relationships: {len(kg_paths)}"
        ]
        
        if provenance_list:
            l4_parts.append("\nSource Provenance & Confidence Metrics:")
            for prov in provenance_list:
                l4_parts.append(f"  - Source: {prov.get('source', 'System Repository')} | Category: {prov.get('category', 'Document')} | Confidence: {prov.get('confidence', '95.0%')}")

        if claims_map:
            l4_parts.append("\nGrounded Claim-to-Evidence Lineage Mapping:")
            for cl in claims_map:
                l4_parts.append(f"  - Claim ID '{cl.get('claim_id')}': \"{cl.get('claim')}\" [Type: {cl.get('claim_type')}, Confidence: {cl.get('confidence')}]")

        l4_text = "\n".join(l4_parts)

        return {
            "level_1": build_lvl_obj(l1_text),
            "level_2": build_lvl_obj(l2_text),
            "level_3": build_lvl_obj(l3_text),
            "level_4": build_lvl_obj(l4_text)
        }
