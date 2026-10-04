# EDQI Synthetic Dataset Implementation Plan: Controlled Defect Injection, Non-Leaky Feature Engineering & Generalization Validation

**Project**: Enterprise AI Decision Intelligence Platform  
**Module**: Enterprise Data Quality Index (EDQI) Machine Learning Engine  
**Dataset Base**: `AB_NYC_2019.csv` (`E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`)  
**Document Status**: CONDITIONALLY APPROVED FOR IMPLEMENTATION  
**Execution Constraint**: READ-ONLY DESIGN REVISION / DO NOT TRAIN / DO NOT MODIFY SOURCE CODE YET  

---

## 1. Executive Summary & Workflow Gate

This amended document specifies the complete technical architecture for generating the controlled synthetic corruption dataset, establishing non-leaky ground-truth labels (`QUALITY_RISK_LEVEL`), guaranteeing zero train/val/test data leakage via pre-corruption base record splitting, isolating statistical transformations, and designing a secondary held-out corruption generalization experiment.

### Final Approval Status:
**CONDITIONALLY APPROVED FOR IMPLEMENTATION**

### Workflow Gate Rules:
- **Current Stage**: Read-Only Design Revision & Plan Amendment.
- **Action Status**: **NO SOURCE CODE MODIFIED**, **NO DATASETS GENERATED**, **NO MODELS TRAINED**.
- **Next Step**: Wait for explicit user instruction before commencing source-code modification and dataset generation.

---

## 2. Base Record Pre-Splitting Workflow (Amendment 1)

To guarantee absolute isolation and prevent synthetic contamination across split boundaries, **pristine base records are split BEFORE any synthetic corruption is generated**.

```
                   30,000 Pristine Base Records (AB_NYC_2019)
                                       │
                      [Assign Unique base_record_id]
                                       │
                [Split Base Records via random_state = 42]
                                       │
       ┌───────────────────────────────┼───────────────────────────────┐
       ▼                               ▼                               ▼
Train Base Records (70%)     Val Base Records (15%)      Test Base Records (15%)
 (~21,000 base listings)      (~4,500 base listings)       (~4,500 base listings)
       │                               │                               │
       ▼ (Independent Corruption)      ▼ (Independent Corruption)      ▼ (Independent Corruption)
Train Synthetic Variants     Val Synthetic Variants      Test Synthetic Variants
 (~42,000 variants)           (~9,000 variants)           (~9,000 variants)
```

### Fundamental Isolation Guarantee:
- $\text{BaseRecordIDs}(\text{Train}) \cap \text{BaseRecordIDs}(\text{Val}) = \emptyset$
- $\text{BaseRecordIDs}(\text{Train}) \cap \text{BaseRecordIDs}(\text{Test}) = \emptyset$
- **Zero Variant Contamination**: No synthetic variant derived from a Train base record will ever appear in Validation or Test sets.
- Final record counts are reported empirically after corruption generation rather than hardcoded.

---

## 3. Varied Synthetic Corruption Protocol (Amendment 2)

To prevent the ML classifier from memorizing static synthetic "magic numbers" (such as always setting `price = 0` or `minimum_nights = 1250`), the corruption generator uses **varied corruption ranges and stochastic parameter sampling** (`random_state=42`).

### Corruption Range Specifications:

| Corruption ID | Target Field(s) | Injection Method & Varied Value Ranges | Severity Category |
|---|---|---|---|
| **C-01** | `name` | Nullify string OR insert random non-printable characters (`"???___"`) | Minor Defect |
| **C-02** | `host_name` | Nullify host string OR set to numerical garbage string (`"999999"`) | Minor Defect |
| **C-03** | `price` | Sample invalid price uniformly from $[-500, 0]$ (e.g., $0, -15, -120, -500$) | Severe Defect |
| **C-04** | `price` | Sample extreme unrealistic price uniformly from $[\$25,000, \$100,000]$ | Severe Defect |
| **C-05** | `minimum_nights` | Sample extreme stay length uniformly from $[366, 1500]$ nights | Severe Defect |
| **C-06** | `minimum_nights` | Sample negative stay length uniformly from $[-30, -1]$ nights | Severe Defect |
| **C-07** | `last_review`, `reviews_per_month` | Set `number_of_reviews` $\in [10, 500]$, but nullify `last_review` & `reviews_per_month` | Severe Defect |
| **C-08** | `number_of_reviews` | Set `number_of_reviews = 0`, but inject valid date `last_review` and rate $> 0` | Severe Defect |
| **C-09** | `latitude`, `longitude` | Sample out-of-bounds latitude $\in [42.0, 90.0] \cup [-90.0, 39.0]$ or longitude $\in [-180.0, -75.0] \cup [-72.0, 180.0]$ | Severe Defect |
| **C-10** | `id`, `name`, `host_id` | Duplicate record with mutated identifier ($id + 900,000$) | Minor Defect |

Every synthetic record retains an exact ground-truth trace in its corruption metadata.

---

## 4. Ground-Truth Metadata vs. ML Feature Separation (Amendment 3)

The dataset schema strictly isolates ground-truth audit metadata from the ML feature matrix:

### 3-Tier Dataset Schema:
1. **Tier A: Raw Source Data**: Original or mutated attribute fields (`price`, `minimum_nights`, `name`, etc.).
2. **Tier B: Audit / Ground-Truth Metadata** (FORBIDDEN FROM ML INPUT):
   - `base_record_id`
   - `synthetic_record_id`
   - `corruption_type`
   - `corruption_severity`
   - `corruption_count`
   - `is_corrupted`
   - `quality_risk_level`
3. **Tier C: ML Feature Matrix**: ONLY the 10 approved feature columns.

> [!CAUTION]
> **FORBIDDEN MODEL INPUTS**: None of the Tier B metadata columns or injection flags will ever enter the model feature matrix during training or inference.

---

## 5. Intentionally Constructed Class Distribution (Amendment 4 & 5)

- **Class Definition**:
  - `QUALITY_RISK_LEVEL = 0` (`HIGH_QUALITY`): 0 injected defects.
  - `QUALITY_RISK_LEVEL = 1` (`MEDIUM_QUALITY`): Exactly 1 minor defect.
  - `QUALITY_RISK_LEVEL = 2` (`POOR_QUALITY`): $\ge 1$ severe defect OR $\ge 2$ combined defects.
- **Classification Nature**:
  - The targeted distribution ($\sim 50\%$ High, $\sim 25\%$ Medium, $\sim 25\%$ Poor) is an **intentionally constructed experimental class distribution**, NOT a natural population statistic of Airbnb data.
- **Class Weighting Strategy**:
  - Do NOT automatically force `class_weight='balanced'`.
  - Inspect the empirical training split distribution after generation. For Random Forest, evaluate if weighting is necessary; for XGBoost, configure multiclass objective params (`multi:softprob`).
  - Never alter test set composition or prediction probabilities to artificially target a specific accuracy.

---

## 6. Held-Out Corruption-Type Generalization Experiment (Amendment 6)

To verify whether the classifier learns generalizable data-quality anomaly patterns rather than merely memorizing synthetic defect signatures, a secondary generalization experiment is designed:

### Generalization Experiment Setup:

| Dataset Split | Corruption Types Included | Purpose |
|---|---|---|
| **Training Split** | C-01, C-02, C-03, C-04, C-05, C-06, C-10 | Model training on standard attribute & range defects |
| **Validation Split** | C-01, C-02, C-03, C-04, C-05, C-06, C-10 | Hyperparameter tuning and model selection |
| **Held-Out Test Split** | **C-07, C-08 (Review Inconsistencies) & C-09 (Spatial Out-of-Bounds)** EXCLUSIVELY | **Evaluate generalization to UNSEEN corruption families** |

- **Rationale**: Review timestamp contradictions (C-07, C-08) and extreme spatial coordinate shifts (C-09) represent distinct structural error modes. Testing on these held-out families proves true data quality risk generalization.

---

## 7. Feature Transformation Leakage Control (Amendment 7)

To prevent statistical test-set contamination:

1. **Group Statistics (`price_to_type_zscore`)**:
   - Compute group mean $\mu_{\text{room\_type, train}}$ and standard deviation $\sigma_{\text{room\_type, train}}$ **ONLY on the Training split**.
   - Apply these training group statistics to transform Validation and Test splits.
2. **Host Listing Density (`host_listing_density`)**:
   - Derived directly from `calculated_host_listings_count` as $\log(1 + \text{listings\_count})$ without global dataset aggregation.
3. **Preprocessing Transformers**:
   - All StandardScalers and missing-value imputers are `fit` **strictly on the Training split** (`fit_transform` on Train, `transform` on Val/Test).

---

## 8. Final Feature Leakage Re-Evaluation (Amendment 8)

| Feature | Raw Source | Transformation | Target Relationship & Safeguard | Leakage Risk | Decision |
|---|---|---|---|---|---|
| `price_log` | `price` | $\log(1 + \max(0, \text{price}))$ | Target assigned via synthetic corruption metadata, decoupling raw price from label | **LOW** | **KEEP** |
| `minimum_nights_log` | `minimum_nights` | $\log(1 + \max(0, \text{min\_nights}))$ | Target assigned via synthetic corruption metadata, decoupling raw stay from label | **LOW** | **KEEP** |
| `number_of_reviews_log` | `number_of_reviews` | $\log(1 + \max(0, \text{reviews}))$ | Continuous review count signal | **LOW** | **KEEP** |
| `reviews_per_month_filled` | `reviews_per_month` | `fillna(0.0)` | Continuous review rate signal | **LOW** | **KEEP** |
| `availability_ratio` | `availability_365` | $\text{clip}(\text{avail} / 365.0, 0, 1)$ | Continuous availability ratio | **LOW** | **KEEP** |
| `host_listing_density` | `calculated_host_listings_count` | $\log(1 + \text{listings})$ | Continuous host density metric | **LOW** | **KEEP** |
| `latitude_raw` | `latitude` | `float(latitude)` | Raw coordinate float | **LOW** | **KEEP** |
| `longitude_raw` | `longitude` | `float(longitude)` | Raw coordinate float | **LOW** | **KEEP** |
| `price_to_type_zscore` | `price`, `room_type` | Z-score using Train $\mu, \sigma$ | Group relative statistical metric (Fit on Train) | **LOW** | **KEEP** |
| `text_length_name` | `name` | `len(str(name))` if not null else 0 | Structural character length | **LOW** | **KEEP** |

---

## 9. Performance Interpretation & No Metric Manipulation (Amendment 9)

- **Strict Rule**: No artificial manipulation of labels, predictions, splits, or corruption severity will be performed solely to force accuracy below 87%.
- **Reporting Rule**: If a leakage-controlled model naturally achieves $> 87\%$ accuracy, the empirical result will be reported as-is, accompanied by an investigation into memorization, duplicate contamination, or synthetic artifacts.

---

## 10. Reproducibility & Random Seed (Amendment 11)

- `random_state = 42` will be enforced across base-record splitting, synthetic defect sampling, variant creation, and classifier training.
- Synthetic generation logic will log full reproducibility metadata (`dataset_hash`, `generation_timestamp`, `seed=42`).

---

## 11. Final Approval Conditions (Amendment 12)

**CONDITIONALLY APPROVED FOR IMPLEMENTATION**

### Implementation Conditions:
1. Base records must be split BEFORE synthetic corruption is generated.
2. Synthetic corruption generator must use varied parameter ranges rather than fixed magic numbers.
3. Tier B corruption metadata must NEVER enter the ML feature matrix.
4. Target labels must come ONLY from synthetic defect ground-truth metadata.
5. Statistical transformations (group z-scores, scalers, imputers) must be fit on Training data ONLY.
6. A secondary held-out corruption-type generalization experiment must be included in evaluation.
7. Metric manipulation is strictly prohibited; report natural empirical accuracy.
8. `random_state = 42` must be enforced throughout.

---

*Plan updated and saved to `E:\project final year\Enterprise-AI-Agentic-Platform\EDQI_SYNTHETIC_DATASET_IMPLEMENTATION_PLAN.md`.*
