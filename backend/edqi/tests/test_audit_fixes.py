from django.test import TestCase
import numpy as np
from edqi.explainability.engines.fallback_engine import FallbackExplainer
from edqi.explainability.recommendation_engine import RecommendationEngine
from edqi.explainability.feature_contribution_builder import FeatureContributionBuilder
from edqi.calculators.quality_score import QualityScoreCalculator

class AuditFixesTestCase(TestCase):
    def test_fallback_age_bounded_scaling(self):
        """
        Verify that extreme record ages do not produce unbounded fallback deviations,
        and that record_age does not completely dominate all other features.
        """
        explainer = FallbackExplainer()
        feature_names = [
            "missing_fields", "invalid_fields", "duplicate_fields", "record_age",
            "quality_score", "completeness_score", "validity_score",
            "consistency_score", "uniqueness_score", "timeliness_score"
        ]

        # Test extreme record age of 1615 days
        clean_features_stale = {
            "missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0,
            "record_age": 1615.0,
            "quality_score": 90.0, "completeness_score": 100.0, "validity_score": 100.0,
            "consistency_score": 100.0, "uniqueness_score": 100.0, "timeliness_score": 0.0
        }
        scaled_inputs = np.array([[float(clean_features_stale[f]) for f in feature_names]])
        
        res = explainer.explain(None, scaled_inputs, feature_names, 0)
        raw_attributions = res["raw_shap_values"]
        
        # Verify age deviation is clamped to -2.0 (scaled by uniform feature importance 0.10 => -0.20)
        self.assertAlmostEqual(raw_attributions["record_age"], -0.20, places=4)
        
        # Process and normalize attributions
        processed = FeatureContributionBuilder.process_contributions(raw_attributions)
        norm_shap = processed["normalized_shap_values"]
        
        # Verify age percentage contribution is bounded (~54.05% based on clamp 2.0) and does not dominate at 99%+
        self.assertLess(norm_shap["record_age"], 60.0)
        self.assertGreater(norm_shap["record_age"], 40.0)

    def test_dynamic_recommendation_expected_improvement(self):
        """
        Verify that expected improvements are calculated dynamically based on quality rules weights,
        rather than returning hardcoded static +4% percentages.
        """
        engine = RecommendationEngine()
        
        # Case A: Timeliness is 0% (stale record), weight is 10% (0.10)
        # Expected dynamic improvement points: (100 - 0) * 0.10 = 10.0 points
        clean_features_stale = {
            "missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0,
            "record_age": 400.0,
            "quality_score": 90.0, "completeness_score": 100.0, "validity_score": 100.0,
            "consistency_score": 100.0, "uniqueness_score": 100.0, "timeliness_score": 0.0
        }
        
        recs = engine.generate_recommendations(clean_features_stale)
        stale_rec = next((r for r in recs if r["recommendation_type"] == "STALE_RECORD"), None)
        
        self.assertIsNotNone(stale_rec)
        self.assertEqual(stale_rec["expected_improvement"], 10.0)

        # Case B: Completeness is 50%, weight is 30% (0.30)
        # Expected dynamic improvement points: (100 - 50) * 0.30 = 15.0 points
        clean_features_incomplete = {
            "missing_fields": 2, "invalid_fields": 0, "duplicate_fields": 0,
            "record_age": 0.0,
            "quality_score": 85.0, "completeness_score": 50.0, "validity_score": 100.0,
            "consistency_score": 100.0, "uniqueness_score": 100.0, "timeliness_score": 100.0
        }
        recs_inc = engine.generate_recommendations(clean_features_incomplete)
        comp_rec = next((r for r in recs_inc if r["recommendation_type"] == "MISSING_REQUIRED_FIELD"), None)
        
        self.assertIsNotNone(comp_rec)
        self.assertEqual(comp_rec["expected_improvement"], 15.0)

    def test_recommendation_triggered_by_violation_only(self):
        """
        Verify that recommendations are strictly triggered by quality violations
        and not raw SHAP attributions.
        """
        engine = RecommendationEngine()
        
        # Perfect record (all violations count 0, timeliness score 100.0)
        clean_features_perfect = {
            "missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0,
            "record_age": 0.0,
            "quality_score": 100.0, "completeness_score": 100.0, "validity_score": 100.0,
            "consistency_score": 100.0, "uniqueness_score": 100.0, "timeliness_score": 100.0
        }
        
        recs = engine.generate_recommendations(clean_features_perfect)
        self.assertEqual(len(recs), 0)

    def test_rule_based_dq_score_remains_unchanged(self):
        """
        Ensure core DQ overall score weighted averages are exactly identical to original specs.
        """
        dimension_scores = {
            "Completeness": 100.0,
            "Validity": 100.0,
            "Consistency": 100.0,
            "Uniqueness": 100.0,
            "Timeliness": 0.0
        }
        rules = {
            "quality_weights": {
                "completeness": 0.30,
                "validity": 0.25,
                "consistency": 0.20,
                "uniqueness": 0.15,
                "timeliness": 0.10
            }
        }
        # Score = (100*0.30 + 100*0.25 + 100*0.20 + 100*0.15 + 0*0.10) / 1.0 = 90.00
        score = QualityScoreCalculator.calculate_score(dimension_scores, rules)
        self.assertEqual(score, 90.0)
