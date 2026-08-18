# EDQI Model Training Evaluation Report

This report presents performance benchmarks, dataset diagnostics, and configuration parameters captured for the training run of the model version **RF_v1.0.0_20260804_155206**.

---

## Model Core Metadata

| Parameter | Value |
| :--- | :--- |
| **Model Version** | `RF_v1.0.0_20260804_155206` |
| **Algorithm** | `RANDOM_FOREST` |
| **Dataset Version** | `v1.0.0` |
| **Feature Version** | `1.0` |
| **Dataset Hash (SHA-256)** | `e8a6d7b0823662079f0f9b5bec71385753576bf5b54fddc799c4920ad4210b6c` |
| **Training Date** | `2026-08-04T10:22:06.594182Z` |
| **Total Features Count** | `10` |

---

## Evaluation Metrics

> [!NOTE]
> Below are accuracy and F1 scores computed across test sets and Stratified K-Fold validation runs.

| Evaluation Metric | Score |
| :--- | :--- |
| **Test Accuracy** | `100.0%` |
| **Test Precision** | `100.0%` |
| **Test Recall** | `100.0%` |
| **Test F1 Score** | `100.0%` |
| **ROC AUC** | `0.0` |
| **Stratified 5-Fold CV Average** | `100.0%` |
| **Best CV Fold Score** | `100.0%` |
| **Worst CV Fold Score** | `100.0%` |

---

## Training Diagnostics

- **Training Records Count:** `14`
- **Testing Records Count:** `6`
- **Validation Records Count:** `3`
- **Model fitting time:** `0.0054 seconds`
- **Model file size:** `0.0044 MB`
- **Explainability Supported:** `True`

---

## Features Importance Mappings

The importance scores computed by the tree estimators:

```json
{
    "missing_fields": 0.2,
    "invalid_fields": 0.0,
    "duplicate_fields": 0.2,
    "record_age": 0.0,
    "quality_score": 0.0,
    "completeness_score": 0.0,
    "validity_score": 0.2,
    "consistency_score": 0.0,
    "uniqueness_score": 0.4,
    "timeliness_score": 0.0
}
```

---

## Training Configuration Parameters

```json
{
    "n_estimators": 5,
    "max_depth": 20,
    "random_state": 42,
    "classes": [
        "Average",
        "Excellent"
    ]
}
```