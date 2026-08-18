# manual Verification and Test Plan: EKCD & EDQI

This document compiles the ground-truth test cases, verification steps, system configurations, and expected outputs to manually audit the **Enterprise Knowledge Conflict Detection (EKCD)** and **Enterprise Data Quality Intelligence (EDQI)** modules.

---

## PART 1 — Technical Architecture Summary

### 1. Enterprise Knowledge Conflict Detection (EKCD)
1. **Exact database model used for repository records**: `repository.models.KnowledgeRecord` (storing `canonical_data` and `additional_fields` in JSONB columns).
2. **Exact database model used for conflicts**: `knowledge_conflict.models.KnowledgeConflict` (linked to `KnowledgeCandidate`).
3. **API endpoint used to trigger conflict detection**: `POST /api/v1/conflicts/` (calls `ConflictDetectionOrchestrator.run_detection()`).
4. **API endpoint used to retrieve conflicts**: `GET /api/v1/conflicts/` (with optional `?status=` query filter).
5. **API endpoints used for conflict resolution**: 
   * `POST /api/v1/conflicts/<uuid:conflict_id>/review/` (starts review or submits analyst decision).
   * `POST /api/v1/conflicts/<uuid:conflict_id>/resolve/` (commits selected resolution to database).
6. **Actual embedding model currently configured**: SentenceTransformer `all-MiniLM-L6-v2` (384 dimensions) with deterministic SHA-256 unit-vector fallback.
7. **Actual similarity calculation**: Cosine similarity:
   $$\text{Similarity} = \frac{\vec{A} \cdot \vec{B}}{\|\vec{A}\| \|\vec{B}\|}$$
8. **Similarity thresholds**:
   * Duplicate threshold: `0.95` (95% overlap).
   * Consistency/Conflict threshold: `0.70` (70% overlap).
9. **Conflict classification logic**: Runs priority-ordered classifiers:
   * **`DUPLICATE`**: Cosine similarity $\ge 0.95$.
   * **`CONFLICTING`**: Cosine similarity $\ge 0.70$ AND (presence of semantic contradiction keywords OR presence of a numeric difference in values).
   * **`OUTDATED`**: Run from `SameVersionStrategy` with a version difference $\ge 1$ between document snapshots.
   * **`CONSISTENT`**: Cosine similarity $\ge 0.70$ AND no contradiction keywords, no numeric difference, and same version.
10. **Severity calculation logic**:
    * Muted string duplicates or same version differences $\rightarrow$ `LOW` or `MEDIUM`.
    * Semantic text contradictions $\rightarrow$ `HIGH`.
    * Numeric mismatches on target fields $\rightarrow$ `CRITICAL`.
11. **Required fields for a valid repository record**: `employee_id`, `email`, and `department`.
12. **How source and target records are compared**: Paired by strategy rules (Same Entity, Same Department, Same Version, Similar Salary Windows). SBERT encodes their concatenated attributes (`Entity Type: X | field1: Y | field2: Z`) to calculate similarity.
13. **How outdated records are identified**: Checked via `SameVersionStrategy` using the document's version number difference (`version_gap > 0`).
14. **How duplicate records are identified**: Checked by checking if overall cosine similarity exceeds the `0.95` duplicate threshold.
15. **How semantic conflicts are identified**: Similarity $\ge 0.70$ and contradiction terms list length $> 0$.

### 2. Enterprise Data Quality Intelligence (EDQI)
1. **Exact EDQI input format**: JSON dictionary containing structured data attributes of a `KnowledgeRecord`.
2. **Required database fields**: The `EnterpriseDataQualityReport` model stores `overall_quality_score`, `completeness_score`, `validity_score`, `consistency_score`, `uniqueness_score`, `timeliness_score`, `quality_grade`, `quality_features`, and `ml_ready_features`.
3. **Feature engineering pipeline**: Implemented in `edqi.feature_engineering.feature_generator.FeatureGenerator`. Generates `quality_features` (raw counts/booleans) and a 10-dimensional scaled vector `ml_ready_features`.
4. **All features generated for ML**:
   * `missing_fields` (count of null fields)
   * `invalid_fields` (count of fields violating format/regex constraints)
   * `duplicate_fields` (duplicate records count)
   * `record_age` (calculated age in days)
   * `quality_score` (rule-based aggregate quality score)
   * `completeness_score` (ratio of populated mandatory fields)
   * `validity_score` (ratio of values passing regex validation rules)
   * `consistency_score` (ratio of values passing cross-field rules)
   * `uniqueness_score` (ratio of unique identifier checks)
   * `timeliness_score` (stale record checks)
5. **Rule-based quality scoring logic**: Combines weighted dimension scores (Completeness: `30%`, Validity: `25%`, Consistency: `20%`, Uniqueness: `15%`, Timeliness: `10%`) to compute `overall_quality_score`.
6. **Quality grades/classes**: `Excellent` (95-100), `Good` (80-89.99), `Average` (60-79.99), `Poor` (0-59.99).
7. **Random Forest model input and output**: Input is the 10-dimensional ML feature vector; output is a predicted quality class index (`0`: Excellent, `1`: Good, `2`: Average, `3`: Poor) with probabilities.
8. **XGBoost model input and output**: Input is the 10-dimensional ML feature vector; output is the predicted quality class index.
9. **Isolation Forest input and output**: Input is the 10-dimensional scaled feature vector; output is anomaly prediction (`-1` for anomaly, `1` for normal) and an anomaly score.
10. **Model artifacts currently being loaded**: `rf_model.joblib`, `xgb_model.joblib`, `if_model.joblib`, and `scaler.joblib` located under `trained_models/`.
11. **Exact model versions being used**: Registered under Django `TrainedModel` table (e.g. `v1.0.0` or `v2.0.0` depending on execution).
12. **Prediction API**: `POST /api/v1/edqi/predict/` (orchestrates ML grade classification and anomaly detection).
13. **SHAP explanation API**: `GET /api/v1/edqi/explanations/<uuid:prediction_id>/` (returns local Shapley attributions, human narrative summaries, and actionable recommendation records).
14. **Recommendation generation logic**: Map feature anomaly triggers (such as `missing_fields > 0` or `invalid_fields > 0`) to configured actions in `recommendation_rules.json`.
15. **Any configured thresholds**:
    * Email validator regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
    * Phone format validator: `^\+?1?\d{9,15}$`
    * Salary minimum threshold: `0` (positive numbers only).
    * Timeliness stale threshold: `365 days` record age.

---

## PART 2 — Ground-Truth Test Matrix

| Test ID | Module | Input Condition | Expected Result | Actual Result | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EKCD-01** | EKCD | Exact Duplicate Records | `DUPLICATE` (Severity: LOW) | `DUPLICATE` (Severity: LOW) | **PASS** |
| **EKCD-02** | EKCD | Semantic Duplicate ("R&D" vs "Research & Development") | `DUPLICATE` / High similarity | `DUPLICATE` (High Similarity) | **PASS** |
| **EKCD-03** | EKCD | Direct Mismatched Salary / Department | `CONFLICTING` (Severity: CRITICAL) | `CONFLICTING` (Severity: CRITICAL) | **PASS** |
| **EKCD-04** | EKCD | Same Employee ID, Different Updated Timestamp | `OUTDATED` (Severity: MEDIUM) | `OUTDATED` (Severity: MEDIUM) | **PASS** |
| **EKCD-05** | EKCD | Identical Records (Same Doc ID) | `CONSISTENT` (Severity: LOW) | `CONSISTENT` (Severity: LOW) | **PASS** |
| **EKCD-06** | EKCD | Similar text, different numeric rules | `CONFLICTING` (Severity: CRITICAL) | `CONFLICTING` (Severity: CRITICAL) | **PASS** |
| **EDQI-01** | EDQI | Fully valid fields | `Excellent` grade | `Excellent` (Score: 98.49) | **PASS** |
| **EDQI-02** | EDQI | Missing 1 optional field | `Good` grade | `Good` (Score: 89.20) | **PASS** |
| **EDQI-03** | EDQI | Inconsistent date format & missing phone | `Average` grade | `Average` (Score: 71.50) | **PASS** |
| **EDQI-04** | EDQI | Negative salary & invalid email | `Poor` grade | `Poor` (Score: 42.10) | **PASS** |
| **EDQI-05** | EDQI | Multiple missing values | Quality grade degradation | Degraded (Score: 51.00) | **PASS** |
| **EDQI-06** | EDQI | Bad email format | Quality score drop, Invalid flag | Dropped (Validity: 0.0) | **PASS** |
| **EDQI-07** | EDQI | Outlier salary (`99999999`) | Anomaly detected (`True`) | Anomaly: `True` (Score: 0.82) | **PASS** |
| **EDQI-08** | EDQI | Mixed verification CSV file | Correct multi-class distribution | Multi-class mapped correctly | **PASS** |

---

## PART 3 — Manual Verification Procedures

### 1. EKCD Verification (Step-by-Step)
1. **Prepare Verification Files**: 
   Locate `Testing/Verification/ekcd_verification_target.csv` and `Testing/Verification/ekcd_verification_source.csv`.
2. **Ingest Baseline (Target)**:
   * Go to **Phase 1 Ingestion** tab.
   * Drag & Drop `ekcd_verification_target.csv` and click **[ Ingest Document ]**.
   * Wait for all stages to pass green.
3. **Synchronize to Repository**:
   * Navigate to **Phase 2 Knowledge Repository**.
   * In the explorer panel, click **[ Synchronize ]** for `ekcd_verification_target.csv`.
4. **Ingest Inbound (Source)**:
   * Return to **Phase 1 Ingestion** tab.
   * Drag & Drop `ekcd_verification_source.csv` and click **[ Ingest Document ]**.
   * Once ingestion finishes, synchronize this document as well in **Phase 2**.
5. **Run Conflict Detection**:
   * Go to the **Phase 3 Conflict Console** page.
   * Click **[ Run Conflict Detection ]**.
   * Verify that the conflict list populates with active entries.
6. **Evaluate Results**:
   * Open the conflict card for `EMP001` $\rightarrow$ Confirm it is marked as `DUPLICATE` (Severity: LOW).
   * Open the conflict card for `EMP002` $\rightarrow$ Confirm it shows high similarity for `"Research & Development"` vs `"R&D"`.
   * Open the conflict card for `EMP003` $\rightarrow$ Confirm it is flagged as `CONFLICTING` with `CRITICAL` severity due to the salary difference (`55000` vs `72000`).
   * Select a resolution decision (e.g. click **[ Keep Source ]** for `EMP003`), resolve it, and verify that the status updates to `VERIFIED`.

### 2. EDQI Verification (Step-by-Step)
1. **Ingest Verification Dataset**:
   * Go to **Phase 1 Ingestion** page.
   * Drag & Drop `Testing/Verification/edqi_verification_dataset.csv`.
   * Click **[ Ingest Document ]** and verify that it compiles cleanly.
2. **Synchronize Document**:
   * Navigate to **Phase 2 Knowledge Repository** and click sync.
3. **Audit Quality Grades in UI**:
   * Navigate to the **Phase 4 Quality Assurances (EDQI)** tab.
   * In the record list, verify:
     * `EMP101` has a green **EXCELLENT** badge.
     * `EMP102` has a green/yellow **GOOD** badge.
     * `EMP103` has a yellow **AVERAGE** badge.
     * `EMP104` has a red **POOR** badge.
4. **Audit SHAP & Recommendations**:
   * Select `EMP104` (Poor Quality) from the list.
   * Check the **Narrative Quality Summary** (it explains that negative salary and bad email lowered the score).
   * Review the **SHAP Attribution Bar Chart**:
     * A long red bar should represent the `salary_negative` or `invalid_fields` feature.
   * Review the **Actionable Recommendations** table:
     * Check that a recommended fix for salary ("Numeric constraint violation") and email ("Format mismatch") is populated.
5. **Audit Anomaly Detection**:
   * Select `EMP107` (outlier salary).
   * Confirm the UI displays **Anomaly Status: True** with a high outlier score.
