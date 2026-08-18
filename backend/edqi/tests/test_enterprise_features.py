import os
import json
import pandas as pd
from django.test import TestCase
from edqi.ml_engine.models import TrainedModel, PredictionHistory
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
from edqi.ml_engine.drift.drift_detector import DriftDetector
from edqi.ml_engine.drift.drift_report_builder import DriftReportBuilder
from edqi.ml_engine.version_manager import VersionManager
from edqi.health.health_engine import HealthEngine
from edqi.builders.evolution_report_builder import EvolutionReportBuilder
from edqi.metrics.metrics_service import MetricsService
from edqi.ml_engine.history.lifecycle_history import LifecycleHistoryLogger

class EnterpriseFeaturesTestCase(TestCase):
    """
    Test suite validating MLOps model governance, dataset evolution, 
    drift detection, platform health scoring, and metrics central service.
    """
    def setUp(self):
        # Create dummy TrainedModels to test version chains
        self.model_a = TrainedModel.objects.create(
            model_name="RF_v1.0.0_test_a",
            version="1.0.0",
            algorithm="Random Forest",
            dataset_version="v1.0.0",
            status="VALIDATING",
            model_path="mock_rf_a.joblib",
            pipeline_path="mock_pipeline_a.joblib"
        )
        self.model_b = TrainedModel.objects.create(
            model_name="RF_v1.0.0_test_b",
            version="1.1.0",
            algorithm="Random Forest",
            dataset_version="v1.1.0",
            status="VALIDATING",
            model_path="mock_rf_b.joblib",
            pipeline_path="mock_pipeline_b.joblib"
        )

        # Mock binary files on disk for synchronization tests
        with open("mock_rf_a.joblib", 'w') as f: f.write("mock")
        with open("mock_pipeline_a.joblib", 'w') as f: f.write("mock")
        with open("mock_rf_b.joblib", 'w') as f: f.write("mock")
        with open("mock_pipeline_b.joblib", 'w') as f: f.write("mock")

        # Clear metrics repository
        from edqi.metrics.metrics_repository import MetricsRepository
        metrics_file = MetricsRepository.get_file_path()
        if os.path.exists(metrics_file):
            os.remove(metrics_file)

    def tearDown(self):
        # Cleanup mock binary files
        for f in ["mock_rf_a.joblib", "mock_pipeline_a.joblib", "mock_rf_b.joblib", "mock_pipeline_b.joblib"]:
            if os.path.exists(f):
                os.remove(f)

        # Clear metrics repository
        from edqi.metrics.metrics_repository import MetricsRepository
        metrics_file = MetricsRepository.get_file_path()
        if os.path.exists(metrics_file):
            os.remove(metrics_file)

    def test_metrics_service(self):
        """
        Validates centralized metrics service recording and querying.
        """
        MetricsService.record_metric("health", "health_score", 95.0, {"env": "test"})
        MetricsService.record_metric("health", "health_score", 85.0, {"env": "test"})
        
        metrics = MetricsService.get_metrics("health", "health_score")
        self.assertEqual(len(metrics), 2)
        
        avg = MetricsService.get_average("health", "health_score")
        self.assertEqual(avg, 90.0)

    def test_model_drift_detection(self):
        """
        Validates that DriftDetector computes correct drift ratios and severity.
        """
        # Create baseline and target dataframes with shift
        baseline = pd.DataFrame({"feat1": [1.0, 1.2, 1.1, 1.3, 1.2]})
        target = pd.DataFrame({"feat1": [3.0, 3.2, 3.1, 3.3, 3.2]}) # Significant mean shift

        res = DriftDetector.detect_drift(baseline, target)
        self.assertEqual(res["drift_percentage"], 100.0)
        self.assertEqual(res["drift_severity"], "HIGH")
        self.assertTrue(res["suggest_retraining"])

    def test_version_management(self):
        """
        Validates model activation lifecycle and chains integrity.
        """
        # Activate model_a
        VersionManager.activate_model("RF_v1.0.0_test_a")
        model_a_updated = TrainedModel.objects.get(model_name="RF_v1.0.0_test_a")
        self.assertEqual(model_a_updated.status, "ACTIVE")
        self.assertIsNotNone(model_a_updated.activated_at)

        # Activate model_b (should retire model_a and chain them)
        VersionManager.activate_model("RF_v1.0.0_test_b")
        model_a_retired = TrainedModel.objects.get(model_name="RF_v1.0.0_test_a")
        model_b_active = TrainedModel.objects.get(model_name="RF_v1.0.0_test_b")

        self.assertEqual(model_a_retired.status, "RETIRED")
        self.assertEqual(model_a_retired.next_version, "RF_v1.0.0_test_b")
        self.assertEqual(model_b_active.status, "ACTIVE")
        self.assertEqual(model_b_active.parent_version, "RF_v1.0.0_test_a")

    def test_database_filesystem_sync(self):
        """
        Validates the DB-FS synchronization and check.
        """
        # Remove model_b file
        if os.path.exists("mock_rf_b.joblib"):
            os.remove("mock_rf_b.joblib")

        res = VersionManager.sync_database_and_filesystem()
        self.assertEqual(res["failed"], 1)
        model_b_failed = TrainedModel.objects.get(model_name="RF_v1.0.0_test_b")
        self.assertEqual(model_b_failed.status, "FAILED")

    def test_health_engine(self):
        """
        Validates Enterprise Health Score calculation logic.
        """
        # Clean Prediction and Reports tables to ensure stable health calculation
        PredictionHistory.objects.all().delete()
        ExplainabilityReport.objects.all().delete()
        RecommendationHistory.objects.all().delete()

        res = HealthEngine.calculate_health()
        self.assertIn("health_score", res)
        self.assertIn("health_grade", res)
        self.assertIn("risk_level", res)

    def test_evolution_report(self):
        """
        Validates evolution logger.
        """
        EvolutionReportBuilder.record_dataset_evolution(
            dataset_version="v2.0.0_test",
            record_count=100,
            feature_count=10,
            dataset_hash="hash_test",
            dataset_size_mb=1.5,
            created_by="UnitTest"
        )
        reports_dir = EvolutionReportBuilder.get_datasets_dir()
        self.assertTrue(os.path.exists(os.path.join(reports_dir, "Dataset_Version_History.json")))
        self.assertTrue(os.path.exists(os.path.join(reports_dir, "Dataset_Version_History.md")))
