import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report as sk_classification_report
from edqi.ml_engine.logging.ml_logger import MLLogger
from edqi.ml_engine.exceptions import EvaluationException

class EvaluationEngine:
    """
    Computes performance benchmark scores (Accuracy, Precision, Recall, F1, ROC AUC, 
    and Confusion Matrix) for classification outputs.
    """
    @classmethod
    def evaluate_model(cls, model_instance, X_test_scaled: np.ndarray, y_test: np.ndarray) -> dict:
        """
        Calculates metric scores for a test dataset.
        """
        MLLogger.evaluation("Starting model evaluation calculations...")
        try:
            # 1. Predict classes
            y_pred = model_instance.predict(X_test_scaled)
            
            # 2. Basic metrics
            acc = float(accuracy_score(y_test, y_pred))
            prec = float(precision_score(y_test, y_pred, average='weighted', zero_division=0))
            rec = float(recall_score(y_test, y_pred, average='weighted', zero_division=0))
            f1 = float(f1_score(y_test, y_pred, average='weighted', zero_division=0))

            # 3. Compute ROC AUC score (multiclass OvR) if probabilities are supported
            roc_auc = 0.0
            if hasattr(model_instance, "predict_proba"):
                try:
                    y_prob = model_instance.predict_proba(X_test_scaled)
                    # Get unique classes present in y_test
                    unique_classes = np.unique(y_test)
                    if len(unique_classes) > 1:
                        # If model returns proba for only the active classes, slice appropriately
                        # or run safe multi-class roc_auc
                        if y_prob.shape[1] == 2 and len(unique_classes) == 2:
                            roc_auc = float(roc_auc_score(y_test, y_prob[:, 1]))
                        else:
                            roc_auc = float(roc_auc_score(y_test, y_prob, multi_class='ovr', average='weighted'))
                except Exception as e:
                    MLLogger.warning(f"ROC AUC computation skipped: {str(e)}")

            # 4. Confusion Matrix & Classification Report
            cm = confusion_matrix(y_test, y_pred)
            report = sk_classification_report(y_test, y_pred, output_dict=True, zero_division=0)
            
            return {
                "accuracy": round(acc, 4),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
                "roc_auc": round(roc_auc, 4),
                "confusion_matrix": cm.tolist(),
                "classification_report": report
            }
        except Exception as e:
            msg = f"Evaluation calculations failed: {str(e)}"
            MLLogger.error(msg)
            raise EvaluationException(msg)
