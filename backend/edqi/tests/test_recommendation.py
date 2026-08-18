from django.test import TestCase
from edqi.calculators.recommendations import RecommendationEngine

class RecommendationEngineTestCase(TestCase):
    def test_missing_field_recommendation(self):
        fix, conf = RecommendationEngine.generate_recommendation("MISSING_FIELD", "department")
        self.assertIn("missing required field", fix)
        self.assertIn("department", fix)
        self.assertEqual(conf, 0.90)

    def test_invalid_email_format_recommendation(self):
        fix, conf = RecommendationEngine.generate_recommendation("INVALID_FORMAT", "email")
        self.assertIn("email address", fix)
        self.assertEqual(conf, 0.98)

    def test_negative_salary_range_recommendation(self):
        fix, conf = RecommendationEngine.generate_recommendation("INVALID_RANGE", "salary")
        self.assertIn("Salary must be a non-negative amount", fix)
        self.assertEqual(conf, 0.99)

    def test_date_inconsistency_recommendation(self):
        fix, conf = RecommendationEngine.generate_recommendation("INCONSISTENT_CROSS_FIELDS", "joining_date")
        self.assertIn("joining date strictly precedes", fix)
        self.assertEqual(conf, 0.99)
