import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer

PRIMARY_DATASET_PATH = r"E:\project final year\Dataset Final\Datasets\HR\IBM_HR_Analytics\IBM HR.csv"
ADDITIONAL_DATASET_PATH = r"E:\project final year\Dataset Final\Datasets\HR\Human_Resources_Data_Set\HR Dataset rheubner.csv"

DROP_COLS = ["Attrition", "EmployeeCount", "Over18", "StandardHours"]

class IBMHRDataPreprocessor:
    """
    Production-quality preprocessing pipeline for IBM HR.csv.
    Enforces strict train/test separation, zero data leakage, and reusable ColumnTransformer.
    """

    def __init__(self, dataset_path: str = PRIMARY_DATASET_PATH, test_size: float = 0.20, random_state: int = 42):
        self.dataset_path = dataset_path
        self.test_size = test_size
        self.random_state = random_state
        self.column_transformer = None
        self.num_cols = []
        self.cat_cols = []
        self.feature_names_out = []

    def load_and_audit(self) -> Tuple[pd.DataFrame, pd.Series]:
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Primary training dataset not found at {self.dataset_path}")
        
        df = pd.read_csv(self.dataset_path)
        if "Attrition" not in df.columns:
            raise KeyError("Target column 'Attrition' not present in IBM HR.csv")

        # Encode target: Yes = 1, No = 0
        y = (df["Attrition"].astype(str).str.strip().str.lower() == "yes").astype(int)
        X = df.drop(columns=DROP_COLS, errors="ignore")

        self.cat_cols = list(X.select_dtypes(include=["object"]).columns)
        self.num_cols = [c for c in X.select_dtypes(include=["int64", "float64"]).columns if c != "EmployeeNumber"]

        return X, y

    def get_train_test_split(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        X, y = self.load_and_audit()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state, stratify=y
        )
        return X_train, X_test, y_train, y_test

    def fit_transform_pipeline(self, X_train: pd.DataFrame) -> np.ndarray:
        self.column_transformer = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), self.num_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), self.cat_cols)
            ]
        )
        X_train_trans = self.column_transformer.fit_transform(X_train)

        # Retrieve feature names out
        cat_encoder = self.column_transformer.named_transformers_["cat"]
        encoded_cat_names = list(cat_encoder.get_feature_names_out(self.cat_cols))
        self.feature_names_out = self.num_cols + encoded_cat_names

        return X_train_trans

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        if self.column_transformer is None:
            raise RuntimeError("ColumnTransformer has not been fitted yet.")
        return self.column_transformer.transform(X)

    def save_preprocessor(self, artifact_path: str):
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        payload = {
            "transformer": self.column_transformer,
            "num_cols": self.num_cols,
            "cat_cols": self.cat_cols,
            "feature_names_out": self.feature_names_out,
            "drop_cols": DROP_COLS,
            "random_state": self.random_state
        }
        joblib.dump(payload, artifact_path)

    @classmethod
    def load_preprocessor(cls, artifact_path: str):
        payload = joblib.load(artifact_path)
        instance = cls(random_state=payload.get("random_state", 42))
        instance.column_transformer = payload["transformer"]
        instance.num_cols = payload["num_cols"]
        instance.cat_cols = payload["cat_cols"]
        instance.feature_names_out = payload["feature_names_out"]
        return instance
