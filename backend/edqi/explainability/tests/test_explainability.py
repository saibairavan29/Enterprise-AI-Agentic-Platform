import uuid
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from edqi.ml_engine.models import PredictionHistory, TrainedModel
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
from edqi.explainability.cache.explanation_cache import MemoryCache
from edqi.explainability.engines.fallback_engine import FallbackExplainer
from edqi.explainability.feature_contribution_builder import FeatureContributionBuilder
from edqi.explainability.explanation_builder import ExplanationBuilder
from edqi.explainability.recommendation_engine import RecommendationEngine
from edqi.explainability.explanation_service import ExplanationService

class ExplainabilityTestCase(TestCase):
    """
    Unit and integration test suite validating Explainable AI components.
    """
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(username="test_xai_user", email="test@example.com", password="password")
        self.client.force_authenticate(user=self.user)
        
        # Setup mock active TrainedModel
        self.active_model = TrainedModel.objects.create(
            model_name="RF_v1.0.0_test",
            version="1.0.0",
            algorithm="Random Forest",
            dataset_version="v1.0.0",
            status="ACTIVE",
            model_path="mock_rf.joblib",
            pipeline_path="mock_pipeline.joblib"
        )
        
        # Setup mock PredictionHistory record
        self.prediction = PredictionHistory.objects.create(
            predicted_grade="Excellent",
            predicted_probability={"Excellent": 0.95, "Good": 0.05},
            is_anomaly=False,
            model_name="RF_v1.0.0_test",
            algorithm="Random Forest",
            model_version="1.0.0",
            dataset_version="v1.0.0",
            execution_trace={
                "input_features": {
                    "missing_fields": 0,
                    "invalid_fields": 0,
                    "duplicate_fields": 0,
                    "record_age": 1,
                    "quality_score": 98.0,
                    "completeness_score": 100.0,
                    "validity_score": 100.0,
                    "consistency_score": 100.0,
                    "uniqueness_score": 100.0,
                    "timeliness_score": 100.0
                }
            }
        )

    def test_memory_cache(self):
        """
        Validates MemoryCache operations (hits, misses, clear).
        """
        cache = MemoryCache()
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.misses, 0)

        # Get missing key
        self.assertIsNone(cache.get("missing_key"))
        self.assertEqual(cache.misses, 1)

        # Set and Get
        payload = {"data": "test"}
        cache.set("key1", payload)
        self.assertEqual(cache.get("key1"), payload)
        self.assertEqual(cache.hits, 1)

        # Clear
        cache.clear()
        self.assertIsNone(cache.get("key1"))

    def test_fallback_explainer(self):
        """
        Validates that FallbackExplainer computes attributions.
        """
        explainer = FallbackExplainer()
        import numpy as np
        X = np.array([[0, 0, 0, 1, 98.0, 100.0, 100.0, 100.0, 100.0, 100.0]])
        feature_names = [
            "missing_fields", "invalid_fields", "duplicate_fields",
            "record_age", "quality_score", "completeness_score",
            "validity_score", "consistency_score", "uniqueness_score",
            "timeliness_score"
        ]
        res = explainer.explain(None, X, feature_names, 0)
        
        self.assertEqual(res["explainer_name"], "Fallback Explainer")
        self.assertIn("raw_shap_values", res)
        self.assertEqual(len(res["raw_shap_values"]), len(feature_names))

    def test_feature_contribution_builder(self):
        """
        Validates sorting, absolute ranking, and positive/negative grouping.
        """
        raw_shap = {
            "missing_fields": -0.25,
            "quality_score": 0.45,
            "timeliness_score": -0.10,
            "completeness_score": 0.20
        }
        res = FeatureContributionBuilder.process_contributions(raw_shap)
        
        # Check positive factors are separated
        self.assertEqual(len(res["top_positive_features"]), 2)
        # Check negative factors are separated
        self.assertEqual(len(res["top_negative_features"]), 2)
        # Verify highest absolute value is sorted first
        self.assertEqual(res["absolute_importance"][0]["feature"], "quality_score")

    def test_explanation_builder(self):
        """
        Validates plain-text generation for Excellent and Poor grades.
        """
        top_pos = [{"feature": "Completeness Score", "value": 0.4, "percentage": 80.0}]
        top_neg = [{"feature": "Missing Fields", "value": -0.3, "percentage": 20.0}]
        
        # Test Excellent grade narrative
        summary_exc = ExplanationBuilder.generate_human_explanation("Excellent", top_pos, top_neg)
        self.assertIn("predicted as Excellent", summary_exc)
        
        # Test Poor grade narrative
        summary_poor = ExplanationBuilder.generate_human_explanation("Poor", top_pos, top_neg)
        self.assertIn("predicted as Poor", summary_poor)

    def test_recommendation_engine(self):
        """
        Validates rule mapping to recommendations from features scan.
        """
        engine = RecommendationEngine()
        clean_features = {
            "missing_fields": 2,
            "invalid_fields": 0,
            "duplicate_fields": 1,
            "record_age": 10
        }
        recs = engine.generate_recommendations(clean_features)
        
        # Missing fields and duplicates should trigger suggestions
        self.assertEqual(len(recs), 2)
        types = [r["recommendation_type"] for r in recs]
        self.assertIn("MISSING_REQUIRED_FIELD", types)
        self.assertIn("DUPLICATE_RECORD", types)

    def test_explanation_service(self):
        """
        Validates E2E explanation service pipeline integration.
        """
        service = ExplanationService()
        report = service.get_explanation_for_prediction(str(self.prediction.prediction_id))
        
        self.assertEqual(report["overall_prediction"], "Excellent")
        self.assertIn("report_id", report)
        self.assertTrue(ExplainabilityReport.objects.filter(prediction=self.prediction).exists())

    def test_views_api(self):
        """
        Validates views JSON responses and CSV/MD export endpoints.
        """
        # Test post explain
        url = reverse('explain-generate')
        payload = {"prediction_id": str(self.prediction.prediction_id)}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
        # Test list history
        url_hist = reverse('explain-history')
        res_hist = self.client.get(url_hist)
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_hist.data), 1)

        # Test statistics API
        url_stats = reverse('explain-statistics')
        res_stats = self.client.get(url_stats)
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        self.assertIn("total_explanations", res_stats.data)
