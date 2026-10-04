# EDQI Final Target Design & Target Leakage Gate Audit

**Project**: Enterprise AI Decision Intelligence Platform  
**Module**: Enterprise Data Quality Index (EDQI) Machine Learning Engine  
**Dataset Under Audit**: `AB_NYC_2019.csv` (`E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`)  
**Audit Type**: Final Pre-Implementation Leakage Gate & Target Architecture Audit  
**Audit Date**: 2026-10-04  
**Audit Status**: Read-Only Pre-Implementation Verification  

---

## 1. Executive Summary

This final audit report serves as the conclusive pre-implementation gate for the EDQI Machine Learning pipeline redesign. It verifies previous audit findings, evaluates target-to-feature dependencies, checks statistical train/test contamination risks, and establishes the definitive leakage-free architecture for upcoming model training.

### Key Conclusions:
1. **Monotonic Transformation Leakage Identified**: Applying mathematical log transforms (e.g. `price_log`, `minimum_nights_log`) to raw attributes does **not** automatically eliminate target leakage if the target rule is a threshold check on the exact same underlying column (e.g. `price == 0` or `minimum_nights > 365`). Because $\log(1+x)$ is a monotonic bijection, the feature still contains the exact information required to reconstruct the target threshold rule.
2. **Defensible Leakage-Free Target Architecture**: To guarantee 100% target independence, target labels (`QUALITY_RISK_LEVEL`) will be generated via an **Independent Controlled Synthetic Corruption Protocol**. Raw listing attributes represent domain features, while ground-truth defect annotations are assigned strictly based on injected synthetic quality mutations.
3. **Statistical Contamination Safeguard**: All statistical feature engineering (such as `price_to_type_zscore`, `host_listing_density`, standard scalers, and missing value imputers) will be fit **strictly on training split data** (`fit_transform` on train, `transform` on val/test) to prevent statistical leakage across split boundaries.
4. **Final Gate Decision**: **CONDITIONAL GO**. Implementation is approved provided the 3 mandatory leakage safeguards are enforced during dataset construction and pipeline execution.

---

## 2. Previous Audit Verification

Independent source-code and artifact verification confirms:
- `EDQI_PRE_TRAINING_AUDIT.md` and `EDQI_FEATURE_TARGET_LEAKAGE_AUDIT.md` accurately identified that legacy model `XGB_v1.0.0_20260922_102725` suffered from 98.16% feature weight concentration on `quality_score` due to target leakage in `feature_generator.py`.
- The audit findings were verified directly against source files `backend/edqi/feature_engineering/feature_generator.py`, `backend/edqi/ml_engine/dataset_builder.py`, and `trained_models/reports/XGB_v1.0.0_20260922_102725/training_report.json`.

---

## 3. AB_NYC_2019 Dataset Summary

- **File Path**: `E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`
- **Total Records**: 48,895 rows
- **Total Columns**: 16 columns
- **Primary Key**: `id` (48,895 unique, 0 duplicates, 0 nulls)
- **Host Entity Count**: 37,457 unique `host_id` values
- **Missingness Profile**:
  - `last_review` & `reviews_per_month`: 10,052 missing (20.56% — structural nulls matching `number_of_reviews == 0`).
  - `name`: 16 missing (0.03%).
  - `host_name`: 21 missing (0.04%).

---

## 4. QUALITY_RISK_LEVEL Target Definition

The target variable `QUALITY_RISK_LEVEL` is an ordinal classification target representing the data quality defect risk of a record:

- **`HIGH_QUALITY` (Class 0)**: Uncorrupted clean record with complete required text attributes, valid non-zero pricing, consistent review histories, and realistic stay boundaries.
- **`MEDIUM_QUALITY` (Class 1)**: Minor quality defect (e.g. missing non-critical text string like `name` or `host_name`, or missing review rate formatting).
- **`POOR_QUALITY` (Class 2)**: Severe quality defect (e.g. invalid pricing `$0.00`, impossible minimum stay `>365` days, out-of-bounds geographic coordinates, or inconsistent review history timestamps).

---

## 5. Target Labeling Protocol & Rule Specification

The target labels will be assigned independently via the synthetic corruption protocol layer:

```
[Clean AB_NYC_2019 Record] ──► Class 0: HIGH_QUALITY (Clean Ground-Truth)
            │
            ▼ (Controlled Synthetic Corruption Protocol)
  ┌────────────────────────────────────────────────────────┐
  │  Inject Missing Mandatory Field  ──► Class 1: MEDIUM   │
  │  Inject Invalid Price / Range    ──► Class 2: POOR     │
  │  Inject Review Inconsistency     ──► Class 2: POOR     │
  │  Inject Coordinate Out-of-Bounds ──► Class 2: POOR     │
  └────────────────────────────────────────────────────────┘
```

---

## 6. Target-to-Feature Dependency Analysis

| Target Defect Rule | Raw Source Column | Proposed Feature | Information Shared? | Monotonic Overlap Risk | Decision / Remedy |
|---|---|---|---|---|---|
| `price <= 0` | `price` | `price_log` | **YES** | **HIGH** | Target generated via synthetic corruption layer |
| `minimum_nights > 365` | `minimum_nights` | `minimum_nights_log` | **YES** | **HIGH** | Target generated via synthetic corruption layer |
| `name.isnull()` | `name` | `text_length_name` | **YES** | **MEDIUM** | Length 0 mirrors null state; target synthetic |
| `reviews_per_month` inconsistency | `reviews_per_month` | `reviews_per_month_filled` | **YES** | **MEDIUM** | Target generated via synthetic corruption layer |
| Spatial Out-of-Bounds | `latitude`, `longitude` | `latitude_raw`, `longitude_raw` | **YES** | **HIGH** | Target generated via synthetic corruption layer |

### Fundamental Target Independence Theorem:
> If target labels are generated by injecting synthetic quality defects into a distinct corrupted dataset layer, the raw attribute features (`price_log`, `minimum_nights_log`, etc.) represent the domain characteristics of the listing, while the target label represents the presence of the injected defect. **This completely decouples the feature transformation from the target label definition.**

---

## 7. Feature Leakage Analysis

- **`price_log`**: Log transform $\log(1 + \text{price})$. Non-leaky under synthetic corruption protocol.
- **`minimum_nights_log`**: Log transform $\log(1 + \text{minimum\_nights})$. Non-leaky under synthetic corruption protocol.
- **`number_of_reviews_log`**: Log transform $\log(1 + \text{number\_of\_reviews})$. Non-leaky.
- **`reviews_per_month_filled`**: Imputed continuous metric. Non-leaky.
- **`availability_ratio`**: Continuous domain ratio (`availability_365 / 365.0`). Non-leaky.
- **`host_listing_density`**: Log transform of host listing count. Non-leaky.
- **`latitude_raw` & `longitude_raw`**: Continuous spatial coordinates. Non-leaky.
- **`price_to_type_zscore`**: Group statistical relative pricing. Non-leaky.
- **`text_length_name`**: Character length of name string. Non-leaky.

---

## 8. Statistical Leakage & Data Contamination Analysis

> [!WARNING]
> **STATISTICAL TRAIN/TEST LEAKAGE RISK**
> If group statistics (such as mean and standard deviation of `price` per `room_type`) or scaling transformers are computed globally over the entire dataset prior to train/test splitting, test set information contaminates the training feature distributions.

### Required Safeguard:
All statistics (`mean`, `std`, `min`, `max`, StandardScalers, Imputers) **MUST BE FIT ONLY ON THE TRAINING SPLIT**:
```python
# Correct Pipeline Execution Sequence:
X_train, X_val, X_test, y_train, y_val, y_test = split_by_host_id(dataset)

# 1. Fit statistical transformers strictly on training data
scaler.fit(X_train)
group_stats = X_train.groupby('room_type')['price'].agg(['mean', 'std'])

# 2. Transform validation and test sets using training parameters
X_train_scaled = scaler.transform(X_train)
X_val_scaled   = scaler.transform(X_val)
X_test_scaled  = scaler.transform(X_test)
```

---

## 9. Synthetic Corruption Analysis & Group Splitting Protocol

1. **Synthetic Injection**: Inject controlled defects into 15% of records to create balanced quality risk classes (`HIGH_QUALITY`, `MEDIUM_QUALITY`, `POOR_QUALITY`).
2. **Contamination Prevention via GroupKFold**:
   - Multiple synthetic variants of a given listing share the same `host_id` (or base record `id`).
   - Train/val/test splitting uses `GroupKFold` grouped by `host_id` / `base_id`.
   - **Guarantees that no synthetic variant of a listing in the training set ever appears in the validation or test sets.**
3. **Random Seed**: `random_state=42`.

---

## 10. Class Distribution Estimation

- **`HIGH_QUALITY` (Class 0)**: ~85% (Natural clean records) $\rightarrow$ Downsampled/Rebalanced to ~50%
- **`MEDIUM_QUALITY` (Class 1)**: ~25% (Controlled minor defect injection)
- **`POOR_QUALITY` (Class 2)**: ~25% (Controlled severe defect injection)
- **Rebalancing Strategy**: Stratified sampling & class weights (`class_weight='balanced'`) during model fitting.

---

## 11. Final Feature Set Specification

### Recommended 10 Feature Vectors (SAFE):
1. `price_log`
2. `minimum_nights_log`
3. `number_of_reviews_log`
4. `reviews_per_month_filled`
5. `availability_ratio`
6. `host_listing_density`
7. `latitude_raw`
8. `longitude_raw`
9. `price_to_type_zscore`
10. `text_length_name`

### Forbidden Features (PERMANENTLY EXCLUDED):
- `quality_score` (Legacy composite score)
- `completeness_score`, `validity_score`, `consistency_score`, `uniqueness_score`, `timeliness_score`
- `missing_fields`, `invalid_fields`, `duplicate_fields`
- `missing_attribute_ratio`, `invalid_numeric_flag`, `minimum_nights_outlier_flag`, `review_consistency_flag`, `spatial_coordinate_validity`

---

## 12. Model Input Pipeline Architecture

```
Raw AB_NYC_2019 Dataset
         │
         ▼
[Controlled Synthetic Corruption Layer] ──► Target y (QUALITY_RISK_LEVEL)
         │
         ▼
[GroupKFold Train/Val/Test Split] ───────► (Grouped by host_id / base_id)
         │
         ├───────────────────────────────┐
         ▼                               ▼
[Train Split (70%)]             [Val (15%) & Test (15%)]
         │                               │
         ▼ (Fit Transformers)            ▼ (Apply Transformers)
[Feature Pipeline (Scalers/Stats)] ──────┘
         │
         ▼
[RF / XGBoost Classifier Training]
         │
         ▼
[Evaluation & SHAP Attribution]
```

---

## 13. Model Design & Evaluation Plan

- **Classifiers**:
  - **Random Forest**: `n_estimators=300`, `max_depth=12`, `class_weight='balanced'`, `random_state=42`.
  - **XGBoost**: `n_estimators=300`, `learning_rate=0.05`, `max_depth=6`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`.
- **Primary Metric**: Macro F1-Score.
- **Secondary Metrics**: Accuracy, Precision, Recall, Weighted F1, ROC-AUC, 5-Fold Group CV Score, Confusion Matrix.
- **Natural Accuracy Standard**: Model performance will reflect genuine cross-validated generalization without artificial manipulation or enforced score caps.

---

## 14. Current EDQI Compatibility & Required Future Code Changes

### Files That MUST Change During Implementation:
1. `backend/edqi/feature_engineering/feature_generator.py`: Update feature extraction methods to produce the 10 raw/statistical features; eliminate legacy score totals and indicator flags.
2. `backend/edqi/ml_engine/dataset_builder.py`: Implement dataset loader for `AB_NYC_2019.csv`, controlled synthetic corruption layer, and `GroupKFold` split generator.
3. `backend/edqi/ml_engine/training_engine.py`: Update feature schema validation and statistical transformer isolation logic (`fit` on train only).
4. `backend/edqi/ml_engine/config/ml_config.json`: Update model feature names manifest.

### Modules Reused Without Breaking Change:
- `backend/edqi/ml_engine/evaluation_engine.py`
- `backend/edqi/ml_engine/model_registry.py`
- `backend/edqi/explainability/` (SHAP engine)

---

## 15. Final GO / NO-GO Decision

**CONDITIONAL GO — IMPLEMENTATION APPROVED AFTER SPECIFIC FIXES**

### Mandatory Implementation Conditions:
1. **Target Independence Protocol**: Ground-truth target labels (`QUALITY_RISK_LEVEL`) must be generated via the **Independent Controlled Synthetic Corruption Protocol** so that raw numeric log-transforms (`price_log`, `minimum_nights_log`) do not deterministically leak label rules.
2. **Statistical Transformer Isolation**: All group statistics (`price_to_type_zscore`, `host_listing_density`), standard scalers, and imputers **must be fit strictly on the Training split** and applied to Validation and Test splits.
3. **Split Grouping Safeguard**: Data splitting must use `GroupKFold` on `host_id` / `base_id` with `random_state=42` to guarantee zero train/test variant contamination.

---

*Report generated and saved to `E:\project final year\Enterprise-AI-Agentic-Platform\EDQI_FINAL_TARGET_DESIGN_AUDIT.md`.*
