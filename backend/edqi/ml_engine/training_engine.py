import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from edqi.ml_engine.exceptions import TrainingException
from edqi.ml_engine.model_registry import ModelRegistry
from edqi.ml_engine.logging.ml_logger import MLLogger
from edqi.ml_engine.validators.feature_schema_validator import EXPECTED_FEATURES

CLASS_MAP = {
    'Excellent': 0,
    'Good': 1,
    'Average': 2,
    'Poor': 3
}

REV_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}

class TrainingEngine:
    """
    Executes dataset splitting, Stratified 5-Fold cross validation, 
    supervised classifier training, and calculates feature importance coefficients.
    """
    def __init__(self, config: dict):
        self.config = config
        self.random_seed = config.get("random_seed", 42)

    def train_classifier(self, algorithm: str, X_scaled: np.ndarray, y: pd.Series) -> dict:
        """
        Runs Stratified 5-Fold Cross Validation and fits the final model.
        Returns a dict containing: model, metrics, and feature importances.
        """
        MLLogger.training(f"Initializing training for: {algorithm}")
        
        # 1. Encode targets to numeric classes contiguously
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        classes_list = le.classes_.tolist()

        # 2. Split dataset (70% train/val, 30% test)
        # Using Stratified split to preserve class ratios
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X_scaled, y_encoded, 
            test_size=self.config.get("test_split_ratio", 0.15) + self.config.get("val_split_ratio", 0.15),
            random_state=self.random_seed,
            stratify=y_encoded
        )

        # Further split train_val into train and validation (if needed for evaluation reporting)
        val_ratio = self.config.get("val_split_ratio", 0.15) / (self.config.get("train_split_ratio", 0.70) + self.config.get("val_split_ratio", 0.15))
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val,
            test_size=val_ratio,
            random_state=self.random_seed,
            stratify=y_train_val
        )

        # 3. Retrieve model hyperparameters from config
        algo_params = self.config.get(algorithm, {})
        
        # 4. Stratified 5-Fold Cross Validation
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_seed)
        
        cv_scores = []
        fold_f1_scores = []
        
        # Unique classes present in current fold targets
        n_classes = len(np.unique(y_encoded))

        for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_val, y_train_val)):
            X_fold_train, X_fold_val = X_train_val[train_idx], X_train_val[val_idx]
            y_fold_train, y_fold_val = y_train_val[train_idx], y_train_val[val_idx]

            fold_model = ModelRegistry.get_model(algorithm, algo_params)
            fold_model.fit(X_fold_train, y_fold_train)
            
            y_fold_pred = fold_model.predict(X_fold_val)
            acc = accuracy_score(y_fold_val, y_fold_pred)
            f1 = f1_score(y_fold_val, y_fold_pred, average='weighted', zero_division=0)
            
            cv_scores.append(acc)
            fold_f1_scores.append(f1)
            MLLogger.info(f"{algorithm} - Fold {fold + 1} accuracy: {round(acc, 4)}, F1: {round(f1, 4)}")

        avg_cv_score = float(np.mean(cv_scores))
        best_fold = float(np.max(cv_scores))
        worst_fold = float(np.min(cv_scores))
        
        MLLogger.training(f"{algorithm} - Stratified 5-Fold CV Average Accuracy: {round(avg_cv_score, 4)}")

        # 5. Fit the final model on train_val
        start_time = time.time()
        final_model = ModelRegistry.get_model(algorithm, algo_params)
        final_model.fit(X_train_val, y_train_val)
        training_time = time.time() - start_time

        # 6. Evaluate final model on Test set
        test_start = time.time()
        from edqi.ml_engine.evaluation_engine import EvaluationEngine
        eval_metrics = EvaluationEngine.evaluate_model(final_model, X_test, y_test)
        prediction_time_sec = (time.time() - test_start) / max(1, len(X_test))

        # 7. Extract Feature Importances
        importances_dict = {}
        if hasattr(final_model, "feature_importances_"):
            importances = final_model.feature_importances_
            for idx, col in enumerate(EXPECTED_FEATURES):
                if idx < len(importances):
                    importances_dict[col] = float(importances[idx])

        metrics = {
            "accuracy": eval_metrics["accuracy"],
            "precision": eval_metrics["precision"],
            "recall": eval_metrics["recall"],
            "f1_score": eval_metrics["f1_score"],
            "roc_auc": eval_metrics["roc_auc"],
            "confusion_matrix": eval_metrics["confusion_matrix"],
            "classification_report": eval_metrics["classification_report"],
            "cross_validation_score": avg_cv_score,
            "best_fold_score": best_fold,
            "worst_fold_score": worst_fold,
            "training_time_sec": training_time,
            "prediction_time_sec": prediction_time_sec,
            "training_dataset_size": len(X_train_val),
            "testing_dataset_size": len(X_test),
            "validation_dataset_size": len(X_val),
            "feature_count": len(EXPECTED_FEATURES),
            "classes": classes_list,
            "cv_results": {
                "fold_accuracies": [float(c) for c in cv_scores],
                "fold_f1_scores": [float(f) for f in fold_f1_scores]
            }
        }

        return {
            "model": final_model,
            "metrics": metrics,
            "feature_importance": importances_dict
        }
