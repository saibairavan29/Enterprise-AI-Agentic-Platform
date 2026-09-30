# EDQI Model Training Evaluation Report

This report presents performance benchmarks, dataset diagnostics, and configuration parameters captured for the training run of the model version **XGB_v1.0.0_20260922_102725**.

---

## Model Core Metadata

| Parameter | Value |
| :--- | :--- |
| **Model Version** | `XGB_v1.0.0_20260922_102725` |
| **Algorithm** | `XGBOOST` |
| **Dataset Version** | `v2.0.0` |
| **Feature Version** | `1.0` |
| **Dataset Hash (SHA-256)** | `ec8a3431af32cd4c61db6897efbd566c291a6448d3d41beef8d433aa6161875c` |
| **Training Date** | `2026-09-22T04:57:25.867377Z` |
| **Total Features Count** | `10` |

---

## Evaluation Metrics

> [!NOTE]
> Below are accuracy and F1 scores computed across test sets and Stratified K-Fold validation runs.

| Evaluation Metric | Score |
| :--- | :--- |
| **Test Accuracy** | `99.53%` |
| **Test Precision** | `99.65%` |
| **Test Recall** | `99.53%` |
| **Test F1 Score** | `99.56%` |
| **ROC AUC** | `1.0` |
| **Stratified 5-Fold CV Average** | `100.0%` |
| **Best CV Fold Score** | `100.0%` |
| **Worst CV Fold Score** | `100.0%` |

---

## Training Diagnostics

- **Training Records Count:** `1002`
- **Testing Records Count:** `430`
- **Validation Records Count:** `177`
- **Model fitting time:** `0.0968 seconds`
- **Model file size:** `0.6147 MB`
- **Explainability Supported:** `True`

---

## Confusion Matrix

```json
[
    [
        365,
        0,
        0
    ],
    [
        0,
        57,
        2
    ],
    [
        0,
        0,
        6
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
        "support": 365.0
    },
    "1": {
        "precision": 1.0,
        "recall": 0.9661016949152542,
        "f1-score": 0.9827586206896551,
        "support": 59.0
    },
    "2": {
        "precision": 0.75,
        "recall": 1.0,
        "f1-score": 0.8571428571428571,
        "support": 6.0
    },
    "accuracy": 0.9953488372093023,
    "macro avg": {
        "precision": 0.9166666666666666,
        "recall": 0.9887005649717514,
        "f1-score": 0.9466338259441708,
        "support": 430.0
    },
    "weighted avg": {
        "precision": 0.9965116279069768,
        "recall": 0.9953488372093023,
        "f1-score": 0.9956409668919693,
        "support": 430.0
    }
}
```

---

## Feature Importance Rankings

The importance scores computed by the tree estimators:

```json
{
    "missing_fields": 0.015093879774212837,
    "invalid_fields": 0.0,
    "duplicate_fields": 0.0032970907632261515,
    "record_age": 0.0,
    "quality_score": 0.981609046459198,
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
    "n_estimators": 300,
    "learning_rate": 0.1,
    "max_depth": 8,
    "random_state": 42,
    "classes": [
        "Average",
        "Excellent",
        "Good"
    ]
}
```