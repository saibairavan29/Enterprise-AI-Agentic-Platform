# Project Progress Report — Enterprise AI Platform

This document details the comprehensive evolution of the **Enterprise AI Platform**, outlining how each module was added, updated, and corrected from the project's inception to its current fully verified production state.

---

## 1. Executive Status
- **Development Cycle Status**: **Session 3 Finalized & Consolidated**.
- **Overall Status**: **Green / Completed**. All four phases are fully operational, verified, and merged.
- **Verification Coverage**: **116/116 backend Django tests** pass cleanly (`OK`); Vite production bundle compiles in 894ms.

---

## 2. E2E Module Changes & Historical Timeline

### Phase 1 — Document Ingestion & Storage Pipeline (Starting Phase)
* **Goal**: Build a secure document ingestion gateway capable of parsing heterogeneous formats while validating integrity.
* **Changes & Additions**:
  - **Added `DocumentUploadService`**: Handles physical file streams, saving uploads securely under `Uploads/raw`.
  - **Added `HashDuplicateValidator`**: Employs SHA-256 hash checks to block redundant uploads, preventing database bloating.
  - **Added `MimeTypeValidator`**: Validates file signatures to prevent extensions mask masquerades (e.g. rejecting binaries named `.pdf`).
  - **Added File Parser Registry**: Added individual extraction modules for `.pdf`, `.xlsx`, `.csv`, `.json`, and `.txt` documents.
  - **Added `IngestionRoutingService`**: Automatically routes successfully parsed files to database persistence tables.
* **Session 3 Updates**:
  - Fixed persistence validation crashes where the document parser returned a single dictionary instead of a list. Updated `PersistenceStage` to wrap single dict parsing outputs inside lists (`records_to_sync`), resolving the pipeline abort error.

---

### Phase 2 — Schema Resolution & Field Mapping Rules
* **Goal**: Standardize heterogeneous headers into a canonical schema for enterprise data consistency.
* **Changes & Additions**:
  - **Added `FieldResolver`**: Employs mapping heuristics to resolve varying headers (e.g. matching `emp_id` to standard `employee_id`).
  - **Added `StandardizationService` & `StandardizationValidator`**: Enforces type checks (e.g., date formats, numeric validation constraints) on incoming fields.
* **Session 3 Updates**:
  - **Resolved Schema Mapping Conflict Exception**:
    - *Problem*: Columns containing generic substrings (like `"name"` matching `"department name"` or `"employment_status"` matching `"employee_id"`) triggered mapping conflicts and duplicate mappings.
    - *Update*: Enhanced `FieldResolver.resolve()` to ignore mapping `"name"`, block substring checks on generic terms (`role`, `type`, `date`, `status`), and prevent `"employee_id"` matching if status/state/type keywords exist in the column headers.

---

### Phase 3 — Logical Repository Boundaries & Streams
* **Goal**: Build secure, role-based document registries with robust rendering.
* **Changes & Additions**:
  - **Added Private vs Public boundaries**: Isolated Personal Repository access to document owners and administrators (unauthorized attempts return `404`). Public/Team repositories are visible to all.
  - **Added `view_file` endpoint**: Enables direct file preview streaming of CSVs, PDFs, images, and text.
* **Session 3 Updates**:
  - **Fixed Seeded Previews 404 Error**:
    - *Problem*: Seeded database records did not have physical raw `source_document` ForeignKey relations on disk, causing the UI to throw preview errors.
    - *Update*: Implemented a fallback file-path resolver in the `view_file` endpoint. If `source_document` is null, the view checks metadata keys (`file.stored_name` or `source.file_path`) and locates raw CSVs in the workspace `Uploads/raw` folders.
  - **Fixed Dashboard Pagination Crash**:
    - *Problem*: Clicking "View" on the admin personal repository triggered `ReferenceError: rowsPerPage is not defined` in `Dashboard.jsx`.
    - *Update*: Declared `const rowsPerPage = 10;` at the top of the component to resolve indices calculations.

---

### Phase 4 — Data Quality & Explainable AI (EDQI)
* **Goal**: Assess record profile metrics and predict qualitative grades using explainable ML.
* **Changes & Additions**:
  - **Added Rule-Based Scoring**: Evaluates Completeness, Validity, Consistency, Uniqueness, and Timeliness metrics to calculate a weighted quality index.
  - **Added RandomForest Classifier**: Predicts data quality classes ("Excellent", "Good", "Average", "Poor") based on quality feature vectors, extracting confidence levels from `predict_proba()`.
  - **Added SHAPTreeExplainer & FallbackExplainer**: Analyzes log-odds prediction attributions of the ML model.
  - **Added config-driven `RecommendationEngine`**: Map quality issues onto recommended fixes.
* **Session 3 Updates**:
  - **Explainability Heading Realignment**: Renamed misleading `"Why This Score? (Model Attributions)"` to `"ML Model Prediction Drivers"` (with explaining subtitle) to clarify it describes the ML prediction, not the absolute DQ score.
  - **Clamped Fallback Age Scaling**: Clamped `record_age` fallback explainer deviation to a stable `[-2.0, 0.0]` range to prevent older records from dominating normalized attribution percentages.
  - **Dynamic Point Mappings**: Configured the recommendation engine to dynamically calculate score points improvements (`Potential score improvement: up to +X points`) based on active weights.
  - **Frontend presentation fixes**: Filtered out zero/negligible drivers and rendered actual feature values in driver logs.

---

## 3. Core Database Models Added
- **`Document` (`ingestion/models.py`)**: Stores raw file hashes, MIME types, and uploads metadata.
- **`KnowledgeDocument` (`repository/models.py`)**: Unified record versions, size, and source link tracking.
- **`EnterpriseDataQualityReport` (`edqi/models.py`)**: Stores rules metrics scores, feature ready vectors, and execution traces.
- **`ExplainabilityReport` (`edqi/explainability/models.py`)**: Stores ML prediction outputs, confidence levels, SHAP attributions, and compilation suggestions.
- **`ConflictReview` (`knowledge_conflict/models.py`)**: Stores similarity comparison pairs, reviewer decisions, and resolved audit trails.
