import re
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('enterprise')

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

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1) -> str:
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
                "num_predict": 1536,
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
        for i, chunk in enumerate(context_chunks[:5], 1):
            if hasattr(chunk, 'to_prompt_text'):
                text_snippet = chunk.to_prompt_text()
            elif isinstance(chunk, dict):
                src = chunk.get('source', 'Document')
                txt = chunk.get('text', '')[:2500]
                text_snippet = f"Evidence #{i} [{src}]: {txt}"
            else:
                text_snippet = f"Evidence #{i}: {str(chunk)[:2500]}"
            doc_evidence_str += text_snippet.strip() + "\n\n"

        kg_evidence_str = ""
        if kg_paths:
            for j, item in enumerate(kg_paths[:5], 1):
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

        system_prompt = (
            "You are an expert Enterprise Knowledge Assistant. Answer the user's question directly, naturally, "
            "and authoritatively using ONLY the provided evidence context.\n"
            "CRITICAL RESPONSE RULES:\n"
            "1. Provide a direct, concise, non-repetitive response directly answering the user's query.\n"
            "2. Do NOT mention internal system terminology such as 'grounded reasoning state', 'SYSTEM GROUNDED CONCLUSION', "
            "'absence of a Knowledge Graph', 'based on the provided document evidence', 'reasoning operation', or 'Here are the key points'.\n"
            "3. Do NOT repeat the same factual statements or numbers multiple times in different paragraphs or bullet lists. State each key insight ONCE cleanly.\n"
            "4. Do NOT output meta-headers such as 'DIRECT FACTS:', 'DETERMINISTIC CALCULATIONS:', or 'DERIVED INSIGHTS & BOUNDARIES:'. State the answer cleanly as regular prose.\n"
            "5. OCR RECEIPT & FINANCIAL SEMANTICS:\n"
            "   a) Preserve the exact semantic distinction between:\n"
            "      - Subtotal / GST-Exclusive Sales Base Amount (the pre-tax taxable sales figure)\n"
            "      - Tax / GST Amount (the tax value itself)\n"
            "      - Total Sales (Incl. GST) / Net Total (the final tax-inclusive payable amount)\n"
            "      - Line Item Total (Quantity x Unit Price, which may be tax-inclusive on retail receipts)\n"
            "      - Rounding Adjustment, Payment Method, and Return Terms\n"
            "   b) Do NOT describe a tax-inclusive net total or tax-inclusive line item total (e.g. 10 x RM5.90 = RM59.00) as a GST-exclusive sales amount if a separate GST-exclusive amount (e.g. RM55.66) and GST tax amount (e.g. RM3.34) exist in the source document.\n"
            "   c) Preserve exact raw OCR text. Do NOT expand OCR fragments, codes, or abbreviations (e.g. if OCR displays 'GCODS', do NOT expand it to 'Goods and Consumption Tax Discounts' unless explicitly expanded in source evidence).\n"
            "   d) Do NOT label package weights, volume sizes, or product specifications (e.g. '300G', '500ML', '2PK') as item numbers or product codes unless explicitly designated as an Item ID/Code in the source text.\n"
            "   e) Do NOT infer or invent vendor names, company names, approval authorities, sign-offs, manager titles, or people unless explicitly written in the source OCR text.\n"
            "6. NUMERIC FIDELITY RULE:\n"
            "   a) All authoritative source numbers, currency figures, percentages, dates, and calculated totals must be reproduced EXACTLY as given in the context.\n"
            "   b) Do NOT alter, truncate, or mistype numeric tokens (e.g. preserve 'INR 1,200,000' exactly; never convert to '1,200,00n' or '1,200,00se').\n"
            "7. REJECTED METRIC PROTECTION:\n"
            "   a) Do NOT output internal reasoning notes about rejected or incompatible metric candidates (e.g. do NOT state that Attendance and Tasks Completed measure different dimensions) unless explicitly requested by the user.\n"
            "8. Only declare 'Insufficient evidence in the provided dataset' if the evidence contains NO relevant information whatsoever to answer any part of the query.\n"
            "9. NO SPECULATION RULE: Do NOT speculate on unstated file contents or state that a file 'likely contains' unmentioned fields or data. Summarize strictly what is explicitly present in the provided evidence. If details are absent, state 'Insufficient evidence in the provided dataset'.\n"
            "10. CAUSALITY vs TEMPORAL PROXIMITY: Temporal proximity or matching projects across documents (e.g. a bill occurring 2 days after an incident) does NOT establish a causal relationship. State temporal facts clearly, but do NOT state or infer that one event caused or was a response to another unless explicit evidence in the source documents states the cause-and-effect relationship."
        )

        grounded_conclusion = grounded_state.get("grounded_conclusion", "")
        comparisons_list = grounded_state.get("comparisons", [])
        conflicts_list = grounded_state.get("conflicts", [])

        comp_str = ""
        for c in comparisons_list:
            comp_str += f"- {c.get('summary')}\n"

        conflict_str = ""
        for conf in conflicts_list:
            conflict_str += f"- {conf.get('conflict_summary')}\n"

        comp_block = f"VERIFIED COMPARISONS:\n{comp_str}\n" if comp_str else ""
        conflict_block = f"DATA CONFLICTS:\n{conflict_str}\n" if conflict_str else ""

        user_prompt = (
            f"QUESTION: {query}\n\n"
            f"SOURCE CONTEXT:\n{doc_evidence_str.strip() or 'No direct document text available.'}\n\n"
            f"{kg_evidence_str.strip()}\n"
            f"{comp_block}"
            f"{conflict_block}\n"
            f"Provide a clear, natural-language response directly answering the question above:"
        )

        llm_response = self.provider.generate(user_prompt, system_prompt=system_prompt, temperature=0.1)
        if llm_response:
            # Strip any accidental preamble prefixes or meta headers
            clean_res = re.sub(
                r'^(Based on the provided document evidence|Based on the provided context|Based on the evidence|According to the provided document evidence|According to the document|The system\'s grounded reasoning state|In the absence of a Knowledge Graph)[,:\s]*',
                '',
                llm_response.strip(),
                flags=re.IGNORECASE
            ).strip()
            
            # Deduplicate repeated identical lines or paragraphs from LLM output
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

            # Post-processing numeric token sanitization against source context
            context_text = " ".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in context_chunks])
            for corr_num, trailing_letter in re.findall(r'\b(\d{1,3}(?:,\d{3})+\d*|\d+)([a-z]{1,2})\b', deduped_res):
                if trailing_letter in ['n', 'se', 'th', 'rd', 'st'] and not deduped_res.lower().endswith(trailing_letter):
                    matched_valid = re.findall(r'\b' + re.escape(corr_num) + r'\d*\b', context_text)
                    if matched_valid:
                        valid_num = matched_valid[0]
                        deduped_res = re.sub(re.escape(corr_num + trailing_letter) + r'\b', valid_num, deduped_res)

            return deduped_res if deduped_res else clean_res

        # Grounded Failsafe Synthesis from evidence chunks & reasoning state if LLM call is delayed or offline
        if query.lower().strip() in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]:
            return "Hello! How can I assist you with your enterprise datasets today?"

        if grounded_conclusion and "Insufficient evidence" not in grounded_conclusion:
            clean_conc = re.sub(r'^(Fact Retrieval|Deterministic Comparison|Deterministic Calculation|Deterministic Aggregation|Knowledge Graph Multi-Hop Reasoning|Conflict Detected|Temporal Change Analysis):\s*', '', grounded_conclusion, flags=re.IGNORECASE).strip()
            clean_conc = re.sub(r'^Verified factual statement from source \'[^\']+\':\s*', '', clean_conc, flags=re.IGNORECASE).strip()
            clean_conc = re.sub(r'^Calculated from authorized records matching criteria [^.]+\.\s*', '', clean_conc, flags=re.IGNORECASE).strip()
            return clean_conc
        elif context_chunks:
            primary_chunk = context_chunks[0]
            if isinstance(primary_chunk, dict):
                raw_txt = primary_chunk.get('text', '')
            else:
                raw_txt = str(primary_chunk)
            
            clean_txt = re.sub(r'^(Structured )?Database Records:\s*', '', raw_txt, flags=re.IGNORECASE).strip()
            clean_txt = re.sub(r'^--- \[Page \d+ of \d+ — Source: [^\]]+\] ---\s*', '', clean_txt).strip()
            return clean_txt[:1500]
        elif kg_paths:
            primary_path = kg_paths[0].get('path_string', '') if isinstance(kg_paths[0], dict) else str(kg_paths[0])
            return f"Knowledge Graph Relationship: {primary_path}"
        else:
            return "Insufficient evidence in the provided dataset"

    def synthesize_progressive_levels(self, query: str, context_chunks: list, kg_paths: list, grounded_reasoning_state: dict = None) -> Dict[str, str]:
        """
        Synthesizes progressive explanation levels (Direct Answer, Detailed Explanation,
        In-depth Reasoning, Comprehensive Analysis) from a single grounded reasoning state.
        """
        base_answer = self.synthesize_answer(query, context_chunks, kg_paths, grounded_reasoning_state)
        # Check for unsupported state
        if "Insufficient evidence" in base_answer or (grounded_reasoning_state and not grounded_reasoning_state.get("is_supported", True)):
            return {
                "level_1": "The available evidence in the authorized dataset does not contain sufficient details to answer this specific query.",
                "level_2": "The retrieved evidence provides general background and context regarding the target document or dataset, but does not explicitly record the specific facts, challenges, or actions requested in the query.",
                "level_3": "While the authorized evidence documents activities, technical tools, and organizational context, those facts do not by themselves establish the specific conclusion requested. Factually distinguishing background information from unsupported inferences ensures grounding integrity.",
                "level_4": "Analysis confirms that the provided source records establish baseline activities and organizational context, but lack specific evidence supporting the queried details. To answer this question authoritatively without ungrounded speculation, additional source documentation or explicit records would be required."
            }

        # Strip internal preambles if present
        clean_base = re.sub(
            r'^(Based on the provided document evidence|Based on the provided context|Based on the evidence|According to the provided document evidence|According to the document|The system\'s grounded reasoning state|In the absence of a Knowledge Graph)[,:\s]*',
            '',
            base_answer.strip(),
            flags=re.IGNORECASE
        ).strip()
        if clean_base:
            clean_base = clean_base[0].upper() + clean_base[1:]

        paragraphs = [p.strip() for p in clean_base.split('\n\n') if p.strip()]
        lines = [line.strip() for line in clean_base.split('\n') if line.strip()]

        # Level 1: Direct Answer (Concise 1-2 sentences)
        if lines:
            l1_text = lines[0]
            if len(lines) > 1 and len(l1_text) < 140:
                l1_text += " " + lines[1]
        else:
            l1_text = clean_base[:250]

        # Level 2: Detailed Explanation (Full natural answer)
        l2_text = clean_base

        # Level 3: In-depth Reasoning (Detailed natural breakdown)
        l3_text = clean_base
        if grounded_reasoning_state:
            claims = grounded_reasoning_state.get("claims_mapping", [])
            claim_texts = [c.get("claim", "") for c in claims if c.get("claim") and c.get("claim") not in clean_base]
            if claim_texts:
                l3_text = clean_base + "\n\n" + "\n".join(f"- {ct}" for ct in claim_texts[:3])

        # Level 4: Comprehensive Analysis (Complete grounded response)
        l4_text = l3_text

        return {
            "level_1": l1_text,
            "level_2": l2_text,
            "level_3": l3_text,
            "level_4": l4_text
        }

