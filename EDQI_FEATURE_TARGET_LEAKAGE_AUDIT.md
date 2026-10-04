# EDQI Second Pre-Training Audit: Proposed Features & Target Leakage Validation

**Project**: Enterprise AI Decision Intelligence Platform  
**Module**: Enterprise Data Quality Index (EDQI) Machine Learning Engine  
**Dataset Under Audit**: `AB_NYC_2019.csv` (`E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`)  
**Audit Type**: Read-Only Target & Feature Leakage Validation  
**Audit Date**: 2026-10-04  

---

## 1. Executive Summary

This second pre-training audit evaluates whether the proposed `AB_NYC_2019` $\rightarrow$ `QUALITY_RISK_LEVEL` machine learning design is genuinely leakage-free and technically sound. 

### Key Findings:
1. **Existing Model Leakage Confirmed**: The existing trained model (`XGB_v1.0.0_20260922_102725`) contains severe target leakage where `quality_score` accounts for **98.16% of feature importance** because `FeatureGenerator` passed `quality_score` directly into the classifier while `DatasetBuilder` derived the target label directly from `quality_score` threshold boundaries.
2. **Leakage Audit of Proposed 10 Features**: A formal dependency analysis reveals that **6 out of the 10 previously proposed features** (`missing_attribute_ratio`, `invalid_numeric_flag`, `text_completeness_ratio`, `spatial_coordinate_validity`, `minimum_nights_outlier_flag`, `review_consistency_flag`) are **explicit rule-indicator flags / defect ratios**. If the `QUALITY_RISK_LEVEL` target is assigned using quality rule conditions, passing these indicator flags creates **direct rule leakage**, causing the classifier to trivially memorize boolean rule trees ($flag = 1 \rightarrow \text{POOR\_QUALITY}$) rather than learning genuine statistical machine learning representations.
3. **Leakage-Free Redesign Proposed**: A completely leakage-free design is formulated wherein **all rule-indicator flags, composite quality scores, and dimension score totals are permanently forbidden from the feature space**. The model receives strictly raw numeric signals, log-transforms, spatial coordinates, and relative statistical z-scores.

---

## 2. Current EDQI Architecture & Workflow

Tracing the exact source-code execution flow in `backend/edqi/`:
```
Raw Dataset (CSV / JSON)
       │
       ▼
[EDQI Analyzers] (completeness, validity, consistency, uniqueness, timeliness)
       │
       ▼
[Quality Calculators] ──► Calculates overall_score (0–100) & quality_grade (A/B/C/D/F)
       │
       ▼
[Feature Generator]  ──► Generates ml_ready_features (INCLUDES overall_score & dimension scores!)
       │
       ▼
[Dataset Builder]    ──► Assigns target y = quality_grade (Derived directly from overall_score)
       │
       ▼
[Training Engine]    ──► Fits Random Forest / XGBoost on Leaky Feature Space (98.16% weight on overall_score)
```

---

## 3. Current Dataset Audit

- **Location**: `E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`
- **Total Records**: 48,895 rows
- **Total Columns**: 16 columns
- **Memory Footprint**: 24.59 MB
- **Primary Key**: `id` (48,895 unique IDs, 0 nulls, 0 duplicate rows)

### Column Attributes & Missingness:

| Column Name | Data Type | Non-Null Count | Null Count | Null % | Unique Count |
|---|---|---|---|---|---|
| `id` | `int64` | 48,895 | 0 | 0.00% | 48,895 |
| `name` | `object` | 48,879 | 16 | 0.03% | 47,905 |
| `host_id` | `int64` | 48,895 | 0 | 0.00% | 37,457 |
| `host_name` | `object` | 48,874 | 21 | 0.04% | 11,452 |
| `neighbourhood_group` | `object` | 48,895 | 0 | 0.00% | 5 |
| `neighbourhood` | `object` | 48,895 | 0 | 0.00% | 221 |
| `latitude` | `float64` | 48,895 | 0 | 0.00% | 19,048 |
| `longitude` | `float64` | 48,895 | 0 | 0.00% | 14,718 |
| `room_type` | `object` | 48,895 | 0 | 0.00% | 3 |
| `price` | `int64` | 48,895 | 0 | 0.00% | 674 |
| `minimum_nights` | `int64` | 48,895 | 0 | 0.00% | 109 |
| `number_of_reviews` | `int64` | 48,895 | 0 | 0.00% | 394 |
| `last_review` | `object` | 38,843 | 10,052 | 20.56% | 1,764 |
| `reviews_per_month` | `float64` | 38,843 | 10,052 | 20.56% | 937 |
| `calculated_host_listings_count` | `int64` | 48,895 | 0 | 0.00% | 47 |
| `availability_365` | `int64` | 48,895 | 0 | 0.00% | 366 |

---

## 4. Current EDQI Target Audit

- **Source File**: `backend/edqi/ml_engine/dataset_builder.py` & `trained_models/reports/XGB_v1.0.0_20260922_102725/training_report.json`
- **Target Name**: `quality_grade`
- **Current Active Classes**: `['Average', 'Excellent', 'Good']`
- **Historical Dataset**: 1,609 synthetic records (1,002 train, 177 val, 430 test) generated from legacy HR/Procurement test sets.

---

## 5. Existing Target Leakage Verification

Verification from current source files:
- **`edqi/feature_engineering/feature_generator.py` (Line 69)**:
  `ml_ready_features` explicitly contains `"quality_score": round(overall_score, 2)`.
- **`edqi/ml_engine/dataset_builder.py`**:
  `y` target values are created by evaluating whether `overall_score >= 90.0` (Excellent), `80.0 <= overall_score < 90.0` (Good), etc.
- **`trained_models/reports/XGB_v1.0.0_20260922_102725/training_report.json`**:
  Feature importance of `quality_score` is **0.981609** (98.16%).

---

## 6. Proposed Target Analysis (`QUALITY_RISK_LEVEL`)

Proposed 3-class target:
- **`HIGH_QUALITY` (Class 0)**: Clean record with 0 rule violations.
- **`MEDIUM_QUALITY` (Class 1)**: Minor defects (e.g. missing non-critical text like `name` or `host_name`).
- **`POOR_QUALITY` (Class 2)**: Severe defects (e.g. `price == 0`, `minimum_nights > 365`, or spatial out-of-bounds).

---

## 7. Audit of the 10 Proposed Features

| # | Feature Name | Source Column(s) | Calculation / Logic | Direct Leakage? | Indirect Leakage? | Leakage Risk | Recommendation |
|---|---|---|---|---|---|---|---|
| 1 | `missing_attribute_ratio` | All columns | Count of nulls / 16 | **YES** | **YES** | **HIGH** | **REMOVE** |
| 2 | `invalid_numeric_flag` | `price`, `minimum_nights` | $\mathbb{I}(\text{price} \le 0 \lor \text{min\_nights} > 365)$ | **YES** | **YES** | **HIGH** | **REMOVE** |
| 3 | `text_completeness_ratio` | `name`, `host_name` | Non-empty text count / total text cols | **YES** | **YES** | **HIGH** | **REMOVE** |
| 4 | `spatial_coordinate_validity` | `latitude`, `longitude` | $\mathbb{I}(\text{coord in NYC box})$ | **YES** | **YES** | **HIGH** | **REMOVE** |
| 5 | `price_to_type_zscore` | `price`, `room_type` | Z-score of price within room_type | **NO** | **NO** | **LOW** | **KEEP** |
| 6 | `minimum_nights_outlier_flag` | `minimum_nights` | $\mathbb{I}(\text{min\_nights} > 365)$ | **YES** | **YES** | **HIGH** | **REMOVE** |
| 7 | `review_consistency_flag` | `number_of_reviews`, `last_review` | $\mathbb{I}(\text{reviews} > 0 \land \text{last\_review is null})$ | **YES** | **YES** | **HIGH** | **REMOVE** |
| 8 | `availability_ratio` | `availability_365` | `availability_365 / 365.0` | **NO** | **NO** | **LOW** | **KEEP** |
| 9 | `host_listing_density` | `calculated_host_listings_count` | $\log(1 + \text{host\_listings})$ | **NO** | **NO** | **LOW** | **KEEP** |
| 10 | `text_length_name` | `name` | `len(str(name))` if name else 0 | **NO** | **NO** | **LOW** | **KEEP** |

---

## 8. Feature-to-Target Dependency & Critical Leakage Analysis

### Critical Leakage Test:
> *"If the model is given these 10 features, can it reconstruct the target without learning a generalizable pattern?"*

**Answer: YES (Severe Rule Leakage in original proposed feature set).**

If the target `QUALITY_RISK_LEVEL` assigns `POOR_QUALITY` whenever `invalid_numeric_flag == 1` or `minimum_nights_outlier_flag == 1` or `review_consistency_flag == 1`, and the model is explicitly fed `invalid_numeric_flag`, `minimum_nights_outlier_flag`, and `review_consistency_flag` as input features, the decision tree will split directly on these binary flags:
$$\text{IF } \text{invalid\_numeric\_flag} == 1 \implies \text{POOR\_QUALITY}$$
This is **rule reproduction**, not machine learning. The model is given explicit boolean indicators of the exact target labeling rules.

---

## 9. Genuine Leakage-Free Design Solution

To create a genuine, leakage-free machine learning task:
1. **Rule Engine**: Evaluates raw records and assigns `QUALITY_RISK_LEVEL` target labels (or controlled synthetic defect labels).
2. **Feature Extractor**: Extracts **only raw domain attributes, log-transformed numeric signals, spatial coordinates, and relative group statistics**.
3. **Strict Prohibition**: **ZERO** rule indicator flags (`invalid_flag`, `missing_ratio`, `is_outlier`, `quality_score`, `completeness_score`) are permitted in the feature space.

---

## 10. Recommended Final Feature Set (10 Non-Leaky Features)

| Feature Name | Source Column(s) | Transformation / Formula | Purpose & Type | Status |
|---|---|---|---|---|
| `price_log` | `price` | $\log(1 + \text{price})$ | Raw numeric signal | **KEEP / NEW** |
| `minimum_nights_log` | `minimum_nights` | $\log(1 + \text{minimum\_nights})$ | Raw numeric signal | **KEEP / NEW** |
| `number_of_reviews_log` | `number_of_reviews` | $\log(1 + \text{number\_of\_reviews})$ | Raw numeric signal | **KEEP / NEW** |
| `reviews_per_month_filled` | `reviews_per_month` | `reviews_per_month.fillna(0.0)` | Raw numeric signal | **KEEP / NEW** |
| `availability_ratio` | `availability_365` | `availability_365 / 365.0` | Continuous domain ratio | **KEEP** |
| `host_listing_density` | `calculated_host_listings_count` | $\log(1 + \text{listings\_count})$ | Continuous host metric | **KEEP** |
| `latitude_raw` | `latitude` | Raw `float64` coordinate | Continuous spatial signal | **KEEP / NEW** |
| `longitude_raw` | `longitude` | Raw `float64` coordinate | Continuous spatial signal | **KEEP / NEW** |
| `price_to_type_zscore` | `price`, `room_type` | Z-score of price within room_type group | Statistical relative metric | **KEEP** |
| `text_length_name` | `name` | `len(str(name))` if name else 0 | Structural text metric | **KEEP** |

### Forbidden Features (Permanently Excluded from ML Input):
- `quality_score`, `completeness_score`, `validity_score`, `consistency_score`, `uniqueness_score`, `timeliness_score`
- `missing_fields`, `invalid_fields`, `duplicate_fields`, `missing_attribute_ratio`
- `invalid_numeric_flag`, `minimum_nights_outlier_flag`, `review_consistency_flag`, `spatial_coordinate_validity`

---

## 11. Synthetic Corruption Protocol & Group Splitting

1. **Controlled Corruption Layer**:
   - Inject defects into a 15% random sample of clean `AB_NYC_2019` records (nullifying mandatory text, corrupting numeric ranges, creating invalid review dates).
   - Label ground-truth: `0 = CLEAN`, `1 = MINOR_DEFECT`, `2 = SEVERE_DEFECT`.
2. **Group Split Integrity**:
   - Group train/test splits by `host_id` (or original listing ID) so that synthetic variants of the same record **never appear in both training and test sets**.
   - Fixed random seed: `random_state=42`.

---

## 12. Model & Evaluation Methodology

- **Classifiers**: Random Forest (`n_estimators=300`, `max_depth=10`, `random_state=42`) and XGBoost (`n_estimators=300`, `learning_rate=0.05`, `max_depth=6`, `random_state=42`).
- **Data Split**: 70% Train, 15% Validation, 15% Test with `GroupKFold` on `host_id`.
- **Primary Metric**: Macro F1-Score (Primary metric for balanced quality evaluation across imbalanced quality classes).
- **Secondary Metrics**: Accuracy, Precision, Recall, ROC-AUC, 5-Fold Cross Validation Score, Confusion Matrix.

---

## 13. Current EDQI Architecture Integration Impact

- **Files That MUST Change**:
  - `backend/edqi/feature_engineering/feature_generator.py` (Remove score totals & indicator flags from `ml_ready_features`; output 10 non-leaky raw/statistical features).
  - `backend/edqi/ml_engine/dataset_builder.py` (Ingest `AB_NYC_2019.csv`, implement controlled corruption layer and non-leaky target generator).
  - `backend/edqi/ml_engine/training_engine.py` (Update feature schema validator and GroupKFold train/val/test splitting).
- **Files That Do NOT Need Architectural Change**:
  - `backend/edqi/ml_engine/evaluation_engine.py` (Reusable metric evaluator).
  - `backend/edqi/ml_engine/model_registry.py` (Reusable versioning registry).
  - `backend/edqi/explainability/` (SHAP explanation engine).

---

## 14. Final Decision

**CONDITIONALLY APPROVED**

### Mandatory Pre-Implementation Conditions:
1. **Rule Indicator Flag Elimination**: All 6 rule indicator flags (`missing_attribute_ratio`, `invalid_numeric_flag`, `text_completeness_ratio`, `spatial_coordinate_validity`, `minimum_nights_outlier_flag`, `review_consistency_flag`) must be **completely removed** from the feature set.
2. **Adopt Non-Leaky Feature Space**: The feature space must consist strictly of the 10 recommended raw numeric/text/spatial signals (`price_log`, `minimum_nights_log`, `number_of_reviews_log`, `reviews_per_month_filled`, `availability_ratio`, `host_listing_density`, `latitude_raw`, `longitude_raw`, `price_to_type_zscore`, `text_length_name`).
3. **Group Split Integrity**: Train/test splitting must use `GroupKFold` on `host_id` / listing ID under `random_state=42`.

---

*Report generated and saved to `E:\project final year\Enterprise-AI-Agentic-Platform\EDQI_FEATURE_TARGET_LEAKAGE_AUDIT.md`.*
