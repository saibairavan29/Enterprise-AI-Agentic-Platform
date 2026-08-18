import json
import os
import hashlib
import time
import pandas as pd
import numpy as np
from datetime import datetime
from edqi.models import EnterpriseDataQualityReport
from edqi.ml_engine.exceptions import DatasetBuilderException
from edqi.ml_engine.validators.feature_schema_validator import FeatureSchemaValidator, EXPECTED_FEATURES
from edqi.ml_engine.logging.ml_logger import MLLogger
from repository.models import KnowledgeDocument

class DatasetBuilder:
    """
    Constructs feature matrices and targets from persisted rule assessment reports,
    performing validations, diagnostics, and SHA-256 fingerprinting.
    """
    @classmethod
    def get_target_class(cls, grade: str) -> str:
        """
        Maps rules letter grade to categorized target classes.
        """
        grade = str(grade).strip().upper()
        if grade in ['A+', 'A']:
            return 'Excellent'
        elif grade == 'B':
            return 'Good'
        elif grade in ['C', 'D']:
            return 'Average'
        else:
            return 'Poor'

    def build_dataset(self, document_id: str = None, dataset_version: str = "v1.0.0") -> tuple:
        """
        Loads assessments, validates features schema, computes metadata hashes,
        and returns (X, y, dataset_metadata).
        """
        MLLogger.dataset(f"Starting dataset build (Document: {document_id or 'ALL'}, Version: {dataset_version})")
        
        # 1. Fetch reports
        query = EnterpriseDataQualityReport.objects.select_related('knowledge_record').all()
        if document_id:
            query = query.filter(knowledge_record__knowledge_document_id=document_id)
            
        reports = list(query)
        if not reports:
            raise DatasetBuilderException("No quality reports found in database to build dataset.")
            
        # 2. Extract feature rows
        rows = []
        labels = []
        for r in reports:
            feats = r.ml_ready_features or {}
            # Strip feature_names if present in the stored dictionary
            clean_feats = {k: v for k, v in feats.items() if k != "feature_names"}
            
            # Pad missing expected features with defaults to allow validator checks
            for col in EXPECTED_FEATURES:
                if col not in clean_feats:
                    clean_feats[col] = 0.0 if col != "record_age" else 0
                    
            rows.append(clean_feats)
            labels.append(self.get_target_class(r.quality_grade))

        # Convert to Pandas DataFrame
        df = pd.DataFrame(rows)
        y = pd.Series(labels)

        # 3. Validate features schema
        FeatureSchemaValidator.validate_dataframe(df)

        # Ensure correct column ordering matching validator list
        df = df[EXPECTED_FEATURES]

        # 4. Generate unique dataset fingerprint
        # Serialize features to CSV to calculate SHA-256 hash
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        dataset_hash = hashlib.sha256(csv_bytes).hexdigest()

        # 5. Calculate data drift metrics
        drift_metrics = {}
        for col in EXPECTED_FEATURES:
            col_series = df[col]
            null_pct = float(col_series.isnull().mean() * 100.0)
            
            # Duplicate values counts
            # Since some features are scores, duplicates are expected, but we measure it
            dup_pct = float(col_series.duplicated().mean() * 100.0)
            
            mean_val = float(col_series.mean()) if not col_series.empty else 0.0
            std_val = float(col_series.std()) if len(col_series) > 1 else 0.0
            min_val = float(col_series.min()) if not col_series.empty else 0.0
            max_val = float(col_series.max()) if not col_series.empty else 0.0

            drift_metrics[col] = {
                "null_percentage": round(null_pct, 4),
                "duplicate_percentage": round(dup_pct, 4),
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "min": round(min_val, 4),
                "max": round(max_val, 4)
            }

        # 6. Build final metadata profile
        metadata = {
            "dataset_version": dataset_version,
            "dataset_hash": dataset_hash,
            "record_count": len(df),
            "feature_count": len(EXPECTED_FEATURES),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "features_diagnostics": drift_metrics
        }

        # Save metadata JSON file locally under output folder
        artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        meta_path = os.path.join(artifacts_dir, "dataset_metadata.json")
        try:
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=4)
            MLLogger.dataset(f"Dataset metadata successfully saved: {meta_path}")
            
            # Save Dataset Evolution History Report
            from edqi.builders.evolution_report_builder import EvolutionReportBuilder
            # Approximate size in MB (number of values * 8 bytes)
            size_bytes = len(df) * len(EXPECTED_FEATURES) * 8.0
            size_mb = size_bytes / (1024.0 * 1024.0)
            EvolutionReportBuilder.record_dataset_evolution(
                dataset_version=dataset_version,
                record_count=len(df),
                feature_count=len(EXPECTED_FEATURES),
                dataset_hash=dataset_hash,
                dataset_size_mb=size_mb,
                created_by="DatasetBuilder"
            )
        except Exception as e:
            MLLogger.error(f"Failed to write dataset metadata file: {str(e)}")

        return df, y, metadata
