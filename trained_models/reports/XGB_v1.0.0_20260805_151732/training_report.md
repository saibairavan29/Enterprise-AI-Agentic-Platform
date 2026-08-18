# EDQI Model Training Evaluation Report

This report presents performance benchmarks, dataset diagnostics, and configuration parameters captured for the training run of the model version **XGB_v1.0.0_20260805_151732**.

---

## Model Core Metadata

| Parameter | Value |
| :--- | :--- |
| **Model Version** | `XGB_v1.0.0_20260805_151732` |
| **Algorithm** | `XGBOOST` |
| **Dataset Version** | `v2.0.0` |
| **Feature Version** | `1.0` |
| **Dataset Hash (SHA-256)** | `d4a05e2852ea5029cdc8d159375b931870c1ce2eefeb239a719975c461431faa` |
| **Training Date** | `2026-08-05T09:47:34.008886Z` |
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
| **ROC AUC** | `1.0` |
| **Stratified 5-Fold CV Average** | `100.0%` |
| **Best CV Fold Score** | `100.0%` |
| **Worst CV Fold Score** | `100.0%` |

---

## Training Diagnostics

- **Training Records Count:** `761`
- **Testing Records Count:** `327`
- **Validation Records Count:** `135`
- **Model fitting time:** `0.0126 seconds`
- **Model file size:** `0.0167 MB`
- **Explainability Supported:** `True`

---

## Confusion Matrix

```json
[
    [
        234,
        0
    ],
    [
        0,
        93
    ]
]
```

---

## Classification Report

```json
{
    "0": {
        "precision": 1.0,
        "recall": 1.0,
        "f1-score": 1.0,
        "support": 234.0
    },
    "1": {
        "precision": 1.0,
        "recall": 1.0,
        "f1-score": 1.0,
        "support": 93.0
    },
    "accuracy": 1.0,
    "macro avg": {
        "precision": 1.0,
        "recall": 1.0,
        "f1-score": 1.0,
        "support": 327.0
    },
    "weighted avg": {
        "precision": 1.0,
        "recall": 1.0,
        "f1-score": 1.0,
        "support": 327.0
    }
}
```

---

## Feature Importance Rankings

The importance scores computed by the tree estimators:

```json
{
    "missing_fields": 1.0,
    "invalid_fields": 0.0,
    "duplicate_fields": 0.0,
    "record_age": 0.0,
    "quality_score": 0.0,
    "completeness_score": 0.0,
    "validity_score": 0.0,
    "consistency_score": 0.0,
    "uniqueness_score": 0.0,
    "timeliness_score": 0.0
}
```

---

## Cross Validation Results

```json
{
    "fold_accuracies": [
        1.0,
        1.0,
        1.0,
        1.0,
        1.0
    ],
    "fold_f1_scores": [
        1.0,
        1.0,
        1.0,
        1.0,
        1.0
    ]
}
```

---

## Training Configuration Parameters

```json
{
    "n_estimators": 10,
    "learning_rate": 0.1,
    "max_depth": 8,
    "random_state": 42,
    "classes": [
        "Average",
        "Good"
    ]
}
```