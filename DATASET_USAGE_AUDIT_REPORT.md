# Dataset Usage Compliance Audit Report

## 1. Dataset to Module Compliance Matrix

| Dataset | Expected Phase | Actual Phase | Actual File | Actual Function | Usage Type | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **IBM HR Analytics Employee Attrition & Performance** | Phase 1, 2, 3, 4, 6 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Human Resources Data Set** | Phase 1, 2, 3, 4 | Phase 1, 2, 3, 4 | `backend/run_e2e_pipeline.py` | `main()` | INGESTION, REPOSITORY, CONFLICT DETECTION, TRAINING, VALIDATION, TESTING | PASS |
| **Superstore Dataset** | Phase 1, 2, 3 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Online Retail Dataset** | Phase 1, 2, 3 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Customer Dataset** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Enron Email Dataset from kaggle** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **AdventureWorks Sample Mfg Database Tables** | Phase 1, 2, 3 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Procurement KPI Analysis Dataset** | Phase 1, 2, 3, 7 | Phase 1, 2, 3 | `backend/run_e2e_pipeline.py` | `main()` | INGESTION, REPOSITORY, CONFLICT DETECTION | PARTIAL (Phase 7 Unimplemented) |
| **Microsoft Annual Reports 2025** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **IBM Annual Reports 2025** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Intel 2025 Annual Reports** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **NIST Cybersecurity Framework** | Phase 1, 2, 3, 6 | None | None | None | UNUSED | FAIL (Documented Only) |
| **FUNSD Dataset** | Phase 1, 2 | None | None | None | UNUSED | FAIL (Documented Only) |
| **SROIE Dataset** | Phase 1, 2 | None | None | None | UNUSED | FAIL (Documented Only) |
| **UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 10-K** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Project Gutenberg(business)** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |
| **Real / Fake Job Posting Prediction** | Phase 1, 2, 3, 4 | None | None | None | UNUSED | FAIL (Documented Only) |
| **DummyJSON API Information** | Phase 1, 2, 3, 5 | None | None | None | UNUSED | FAIL (Documented Only) |

---

## 2. Phase 5 Knowledge Intelligence Dataset Readiness

| Dataset | Available | Parsed | Chunked | Embedded | KG Entities | KG Relations | Ontology | Semantic Retrieval | RAG | LLM | Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer Dataset** | YES (API Specs) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **Enron Email Dataset** | YES (1.36 GB CSV) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **Microsoft Annual Reports** | YES (DOCX) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **IBM Annual Reports** | YES (PDF) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **Intel Annual Reports** | YES (PDF) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **SEC Form 10-K** | YES (MHTML) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **Project Gutenberg Business** | YES (HTML/ZIP) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |
| **DummyJSON API Information** | YES (API Specs) | NO | NO | NO | NO | NO | NO | NO | NO | NO | NO |

> [!NOTE]
> All Phase 5 Knowledge Assistant features are currently marked **NOT IMPLEMENTED** because the `knowledge_assistant` app directory contains only empty Django file stubs.

---

## 3. Knowledge Graph & RAG Requirements Checklist

| Requirement | Status | Files / Functions Mapped |
| :--- | :--- | :--- |
| **1. Knowledge Graph** | MISSING | None |
| **2. Ontology-based representation** | MISSING | None |
| **3. Entity extraction** | MISSING | None |
| **4. Relationship extraction** | MISSING | None |
| **5. Entity normalization** | MISSING | None |
| **6. Semantic retrieval** | MISSING | None |
| **7. Graph retrieval** | MISSING | None |
| **8. Hybrid graph + vector retrieval** | MISSING | None |
| **9. Dynamic knowledge orchestration** | MISSING | None |
| **10. Multi-level explanation** | MISSING | None |
| **11. Source provenance** | MISSING | None |
| **12. Evidence tracing** | MISSING | None |
