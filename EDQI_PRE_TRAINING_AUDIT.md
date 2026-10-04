# EDQI Pre-Training Audit

**Project**: Enterprise AI Decision Intelligence Platform  
**Module**: Enterprise Data Quality Index (EDQI) Machine Learning Engine  
**Dataset Under Audit**: `AB_NYC_2019.csv` (`E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`)  
**Audit Date**: 2026-10-04  
**Audit Mode**: Read-Only Pre-Training Verification  

---

## 1. Project Root

- **Target Search Location**: `E:\project final year\`
- **Discovered Project Root**: `E:\project final year\Enterprise-AI-Agentic-Platform\`
- **Verification Evidence**:
  - `backend/` (Django 5.0 REST API workspace)
  - `frontend/` (React 18 + Vite frontend workspace)
  - `backend/edqi/` (EDQI module location)
  - `trained_models/` (Model storage and version registry)
  - `backend/manage.py` (Django entrypoint)
  - `requirements.txt` (Dependencies specification)
- **Dataset Path**: `E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`

---

## 2. Project Architecture Summary

- **Backend Framework**: Django 5.0.1, Python 3.11.9
- **Frontend Framework**: React 18, Vite 5, Tailwind CSS
- **Database Engine**: SQLite 3 (Django ORM with model isolation)
- **ML / AI Stack**: `scikit-learn` 1.7.1, `xgboost` 3.0.3, `numpy` 1.26.4, `pandas` 2.3.1, `joblib` 1.5.1
- **Model Storage**: `trained_models/` (Root-level persistent registry with subdirectories for `random_forest`, `xgboost`, `isolation_forest`, `manifests`, `reports`, `pipelines`, and `feature_history`)
- **API Structure**:
  - `/api/v1/edqi/` (EDQI profiling, assessment, and ML predictions)
  - `/api/v1/knowledge-assistant/` (RAG and Reasoning Engine)
  - `/api/v1/policy-simulator/` (Policy impact analysis & SHAP)
- **EDQI Location**: `E:\project final year\Enterprise-AI-Agentic-Platform\backend\edqi\`
- **ML Engine Location**: `E:\project final year\Enterprise-AI-Agentic-Platform\backend\edqi\ml_engine\`

---

## 3. Current EDQI Architecture

The existing EDQI implementation comprises a dual-layer quality architecture:

1. **Rule-Based Deterministic Quality Layer**:
   - `analyzers/`: Modular dimension analyzers (`completeness_analyzer.py`, `validity_analyzer.py`, `consistency_analyzer.py`, `uniqueness_analyzer.py`, `timeliness_analyzer.py`, `text_fraud_analyzer.py`).
   - `calculators/`: Aggregates dimension scores into an overall quality score (`quality_score.py`) and maps scores to letter grades (`quality_grade.py`).
2. **Supervised ML Assessment Layer**:
   - `feature_engineering/feature_generator.py`: Converts rule analyzer outputs and dimension scores into numerical feature vectors.
   - `ml_engine/dataset_builder.py`: Synthesizes evaluation datasets from raw/dirty records and assigns ground-truth labels.
   - `ml_engine/training_engine.py`: Performs Stratified 5-Fold Cross Validation and fits Random Forest / XGBoost classifiers.
   - `ml_engine/evaluation_engine.py`: Computes precision, recall, F1, ROC-AUC, confusion matrix, and feature importances.
   - `ml_engine/model_registry.py`: Handles model versioning, artifact persistence, and metadata manifests.

---

## 4. Current EDQI Dataset

- **Previous Training Dataset Size**: 1,609 total records (synthesized across `sample_dirty_hr_dataset.csv` and `sample_dirty_procurement_dataset.json`).
- **Train/Val/Test Split Ratio**: 70% Train (1,002 records), 15% Validation (177 records), 15% Test (430 records).
- **Previous Dataset Hash**: `ec8a3431af32cd4c61db6897efbd566c291a6448d3d41beef8d433aa6161875c` (v2.0.0).

---

## 5. Current EDQI Features

The previous ML pipeline (`feature_generator.py`) generated 10 features for classifier input:

1. `missing_fields` (Integer count of missing field issues)
2. `invalid_fields` (Integer count of range/format/value invalidities)
3. `duplicate_fields` (Integer count of duplicate record issues)
4. `record_age` (Integer record age in days)
5. `quality_score` (Float overall composite quality score, 0–100)
6. `completeness_score` (Float completeness dimension score, 0–100)
7. `validity_score` (Float validity dimension score, 0–100)
8. `consistency_score` (Float consistency dimension score, 0–100)
9. `uniqueness_score` (Float uniqueness dimension score, 0–100)
10. `timeliness_score` (Float timeliness dimension score, 0–100)

---

## 6. Current EDQI Target

- **Target Label Name**: `quality_grade`
- **Classes**: `["Excellent", "Good", "Average"]` (in latest trained version `XGB_v1.0.0_20260922_102725`).
- **Target Mapping Logic**:
  - `overall_score >= 90.0` $\rightarrow$ `Excellent`
  - `80.0 <= overall_score < 90.0` $\rightarrow$ `Good`
  - `60.0 <= overall_score < 80.0` $\rightarrow$ `Average`
  - `overall_score < 60.0` $\rightarrow$ `Poor`

---

## 7. Current Training Pipeline

- **Splitting**: Stratified split with `random_state=42` (70% train/val, 30% test; train/val split into 70% train, 15% val, 15% test).
- **Cross-Validation**: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
- **Scaling**: Standardized scaling via `feature_pipeline.joblib`.
- **Hyperparameters**:
  - **Random Forest**: `n_estimators=300`, `max_depth=12`, `random_state=42`.
  - **XGBoost**: `n_estimators=300`, `learning_rate=0.1`, `max_depth=8`, `random_state=42`.

---

## 8. Existing Model Artifacts Audit

An inspection of `trained_models/` reveals the following model versions:

| Model Version | Algorithm | Date | Features | Accuracy | F1-Score | Status / Compatibility |
|---|---|---|---|---|---|---|
| `RF_v1.0.0_20260922_102725` | Random Forest | 2026-09-22 | 10 | 99.53% | 0.9956 | Active (Trained on old synthetic data) |
| `XGB_v1.0.0_20260922_102725` | XGBoost | 2026-09-22 | 10 | 99.53% | 0.9956 | Active (Trained on old synthetic data) |
| `ISO_v1.0.0_20260922_102725` | Isolation Forest | 2026-09-22 | 10 | N/A | N/A | Active (Unsupervised anomaly detector) |

---

## 9. Previous Target Leakage Analysis

> [!CAUTION]
> **CRITICAL FINDING: PREVIOUS TARGET LEAKAGE CONFIRMED**

### Source-Code Proof of Target Leakage:
1. **Target Derivation (`edqi/ml_engine/dataset_builder.py` & `edqi/calculators/quality_grade.py`)**:
   The ground-truth classification target `y` (`quality_grade`) was derived directly by applying threshold boundaries to `overall_score` (calculated as the weighted sum of `completeness_score`, `validity_score`, `consistency_score`, `uniqueness_score`, and `timeliness_score`).
2. **Feature Generation (`edqi/feature_engineering/feature_generator.py`, Lines 65-75)**:
   The `FeatureGenerator.generate_features()` method explicitly included `quality_score` (the composite score itself) AND all 5 dimension score totals (`completeness_score`, `validity_score`, `consistency_score`, `uniqueness_score`, `timeliness_score`) inside `ml_ready_features`.
3. **Empirical Artifact Evidence (`trained_models/reports/XGB_v1.0.0_20260922_102725/training_report.json`)**:
   In the trained model's feature importance output:
   ```json
   "feature_importance": {
       "quality_score": 0.981609046459198,
       "missing_fields": 0.015093879774212837,
       "duplicate_fields": 0.0032970907632261515,
       "invalid_fields": 0.0
   }
   ```
   `quality_score` accounted for **98.16% of the model's total decision weight**. The model was simply memorizing `if quality_score >= 90 then Excellent`, yielding artificial 99.53% accuracy without learning true statistical data quality patterns.

---

## 10. AB_NYC_2019 Dataset Analysis

- **File Path**: `E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv`
- **Total Rows**: 48,895
- **Total Columns**: 16
- **Memory Usage**: 24,592,128 bytes (~24.6 MB)
- **Primary Key Candidate**: `id` (48,895 unique, 0 nulls, 0 duplicate rows)

### Column Details & Missingness:

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

### Numerical Summary Statistics:

| Column | Min | 25% | Median (50%) | 75% | Max | Mean | Std Dev |
|---|---|---|---|---|---|---|---|
| `price` | 0 | $69.00 | $106.00 | $175.00 | $10,000 | $152.72 | $240.15 |
| `minimum_nights` | 1 | 1 | 3 | 5 | 1,250 | 7.03 | 20.51 |
| `number_of_reviews` | 0 | 1 | 5 | 24 | 629 | 23.27 | 44.55 |
| `reviews_per_month` | 0.01 | 0.19 | 0.72 | 2.02 | 58.50 | 1.37 | 1.68 |
| `calculated_host_listings_count` | 1 | 1 | 1 | 2 | 327 | 7.14 | 32.99 |
| `availability_365` | 0 | 0 | 45 | 227 | 365 | 112.78 | 131.62 |

---

## 11. Data Quality Findings

1. **Missingness Correlation**:
   - `last_review` and `reviews_per_month` are missing for **exactly 10,052 records** (20.56%).
   - This missingness corresponds 1:1 with `number_of_reviews == 0`. When a listing has 0 reviews, review dates and review rates are structurally absent.
2. **Invalid Numeric Data**:
   - **`price == 0`**: Exactly 11 listings have a price of $0.00. This is an invalid domain value for rental listings.
3. **Missing Critical Text Attributes**:
   - `name`: 16 missing records.
   - `host_name`: 21 missing records.
4. **Extreme Business Logic Outliers**:
   - `minimum_nights`: Maximum value is 1,250 nights (~3.4 years minimum stay requirement).
   - `calculated_host_listings_count`: Maximum value is 327 listings for a single host entity (`Sonder (NYC)`).
   - `availability_365`: 17,533 listings (35.86%) have 0 days availability.

---

## 12. Quality Issue Catalogue

| Rule ID | Affected Column(s) | Detection Method | Affected Row Count | Percentage | Example / Detail | Quality Impact | Confidence |
|---|---|---|---|---|---|---|---|
| `R001` | `price` | `price == 0` | 11 | 0.02% | Listing ID `20333471` (`price=0`) | Invalid domain value | **VALIDATED** |
| `R002` | `name` | `name.isnull()` | 16 | 0.03% | Listing ID `1615764` (`name=NaN`) | Missing mandatory attribute | **VALIDATED** |
| `R003` | `host_name` | `host_name.isnull()` | 21 | 0.04% | Listing ID `3256776` (`host_name=NaN`) | Missing entity name | **VALIDATED** |
| `R004` | `minimum_nights` | `minimum_nights > 365` | 14 | 0.03% | Listing ID `14022736` (`min_nights=1250`) | Extreme unrealistic boundary | **LIKELY** |
| `R005` | `last_review`, `reviews_per_month` | `num_reviews > 0 & last_review.isnull()` | 0 | 0.00% | All 10,052 missing review dates have `num_reviews == 0` | Structural missingness (expected) | **VALIDATED** |
| `R006` | `latitude`, `longitude` | Out-of-bounds NYC bounding box | 0 | 0.00% | All lat (40.49–40.91), lon (-74.25– -73.71) | Spatial integrity clean | **VALIDATED** |

---

## 13. Native Quality Label Availability

> [!IMPORTANT]
> `AB_NYC_2019.csv` **does NOT contain a native binary or ordinal data quality label column** (such as `is_defective` or `quality_grade`).
> It is an unannotated, real-world public dataset. Therefore, a **rigorous, non-leaky target design** must be constructed prior to model training.

---

## 14. Proposed Target Options

### Option A: Ordinal Record Quality Risk Index (`QUALITY_RISK_LEVEL`) — RECOMMENDED
Construct a 3-class target based on objective rule violations:
- **`HIGH_QUALITY` (Class 0)**: 0 rule violations, complete text fields, valid price (>0), realistic minimum nights ($\le 365$).
- **`MEDIUM_QUALITY` (Class 1)**: Minor defects (e.g., zero availability with low review count, or missing non-critical text attribute like `name`).
- **`POOR_QUALITY` (Class 2)**: Severe data defects (e.g., `price == 0`, `minimum_nights > 365`, or multiple missing/invalid attributes).

### Option B: Binary Defect Risk Label (`HAS_QUALITY_DEFECT`)
- **`CLEAN` (0)**: Zero quality rule violations.
- **`DEFECTIVE` (1)**: 1 or more quality rule violations.

---

## 15. Synthetic Corruption Assessment

Because naturally occurring defects in `AB_NYC_2019.csv` are low (0.02% invalid price, 0.03% missing name), controlled synthetic corruption is **necessary** to train a robust supervised classifier across all 5 EDQI quality dimensions:

1. **Controlled Injection Protocol**:
   - Inject missing values (nullify random non-PK attributes in 5% of records).
   - Inject range/format invalidities (`price = -50`, `price = 0`, `latitude = 999.0`).
   - Inject consistency violations (`number_of_reviews > 0` but `last_review` set to null).
   - Inject duplicate records (duplicate 2% of records with slight text mutations).
2. **Reproducibility Guarantee**: Fixed random seed (`random_state=42`).
3. **Non-Leakage Guarantee**: Corruption metadata (such as `is_corrupted` flag) will **never** be passed as a feature to the model.

---

## 16. Proposed Final ML Features

To eliminate target leakage, **no composite quality scores or dimension score totals will be provided to the model**. Instead, the model will receive normalized attribute-level structural features:

1. `missing_attribute_ratio` (Ratio of null fields in record)
2. `invalid_numeric_flag` (Binary indicator of invalid numeric range)
3. `text_completeness_ratio` (Ratio of non-empty text string attributes)
4. `spatial_coordinate_validity` (Binary indicator of NYC coordinate bounding box)
5. `price_to_type_zscore` (Z-score of price relative to room_type group)
6. `minimum_nights_outlier_flag` (Binary flag for `minimum_nights > 365`)
7. `review_consistency_flag` (Binary flag for inconsistency between `number_of_reviews` and `reviews_per_month`)
8. `availability_ratio` (`availability_365 / 365.0`)
9. `host_listing_density` (Log-transformed `calculated_host_listings_count`)
10. `text_length_name` (Character length of listing name string)

---

## 17. Formal Leakage Analysis

| Proposed Feature | Used to Derive Target? | Leakage Risk? | Action / Safeguard |
|---|---|---|---|
| `missing_attribute_ratio` | Indirectly evaluated | **NO** | Calculated from raw fields, not score calculators |
| `invalid_numeric_flag` | Indirectly evaluated | **NO** | Raw boolean check on numeric boundaries |
| `price_to_type_zscore` | No | **NO** | Statistical relative metric |
| `overall_score` (OLD FEATURE) | Yes (Directly derived label) | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |
| `completeness_score` (OLD) | Yes | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |
| `validity_score` (OLD) | Yes | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |
| `consistency_score` (OLD) | Yes | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |
| `uniqueness_score` (OLD) | Yes | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |
| `timeliness_score` (OLD) | Yes | **YES (HIGH)** | **EXCLUDED PERMANENTLY** |

---

## 18. Proposed Model Design

Both **Random Forest** and **XGBoost** will be trained and comparatively benchmarked:

1. **Random Forest Classifier**:
   - `n_estimators=300`, `max_depth=12`, `min_samples_split=5`, `random_state=42`.
   - Serves as a robust non-linear tabular baseline resistant to overfitting.
2. **XGBoost Classifier**:
   - `n_estimators=300`, `learning_rate=0.05`, `max_depth=6`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`.
   - Provides high-capacity gradient boosting with SHAP tree explainability support.

---

## 19. Proposed Evaluation Methodology

- **Dataset Split**: 70% Train, 15% Validation, 15% Test.
- **Grouped Splitting**: `GroupKFold` on `host_id` (or original listing ID for synthetic variants) to prevent data leakage across split boundaries.
- **Metrics**: Accuracy, Macro Precision, Macro Recall, Macro F1-Score, Weighted F1-Score, ROC-AUC, 5-Fold CV Score, Confusion Matrix.
- **Random Seed**: `random_state=42`.

---

## 20. Proposed EDQI Integration Architecture

```
Raw Tabular Data (AB_NYC_2019)
       │
       ▼
[EDQI Analyzers & Rule Engine] ───► Deterministic Score & Grade
       │
       ▼
[Non-Leaky Feature Engineering] ──► Raw Feature Vector (10 structural features)
       │
       ▼
[Trained RF / XGBoost Models] ────► Supervised Quality Risk Prediction & Probability
       │
       ▼
[SHAP Explanation Engine] ────────► Feature Attribution & Risk Recommendations
```

---

## 21. Proposed Model Artifact Design

Artifacts will be persisted in `trained_models/` following standard versioning:
- `random_forest/RF_v2.0.0_<timestamp>/classifier.joblib`
- `xgboost/XGB_v2.0.0_<timestamp>/classifier.joblib`
- `manifests/XGB_v2.0.0_<timestamp>/reproducibility_manifest.json`
- `reports/XGB_v2.0.0_<timestamp>/training_report.json`
- `pipelines/feature_pipeline.joblib`

---

## 22. Existing Tests Audit

Existing unit tests in `backend/edqi/tests/` and `backend/edqi/ml_engine/tests/` cover:
- `test_analyzers.py`: Dimension analyzer rule checks.
- `test_assessment.py`: Assessment service integration.
- `test_training.py`: Training engine execution.
- `test_prediction.py`: Prediction service inference.
- `test_feature_pipeline.py`: Feature transformer pipelines.

---

## 23. Proposed Additional Tests

1. `test_target_leakage_prevention.py`: Assert `quality_score`, `completeness_score`, and overall scores are absent from training feature names.
2. `test_ab_nyc_dataset_ingestion.py`: Verify reading, cleaning, and feature extraction from `AB_NYC_2019.csv`.
3. `test_synthetic_corruption_reproducibility.py`: Verify corrupted record counts under `random_state=42`.

---

## 24. Risks and Limitations

- **Synthetic Distortion**: Over-corrupting real-world listings may distort domain price distributions if not bounded realistically.
- **Group Leakage**: Multiple listings owned by the same `host_id` must be grouped together during train/test splits to avoid memory leakage across splits.

---

## 25. FINAL RECOMMENDATION

**APPROVED TO PROCEED**

*(Pending explicit user approval of this pre-training audit before executing dataset construction, model training, and source-code integration).*

