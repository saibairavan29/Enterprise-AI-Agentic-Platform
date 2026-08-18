import re
from django.test import TestCase
from edqi.models import DataQualityDimension
from edqi.analyzers.completeness_analyzer import CompletenessAnalyzer
from edqi.analyzers.validity_analyzer import ValidityAnalyzer
from edqi.analyzers.consistency_analyzer import ConsistencyAnalyzer
from edqi.analyzers.uniqueness_analyzer import UniquenessAnalyzer
from edqi.analyzers.timeliness_analyzer import TimelinessAnalyzer
from edqi.calculators.quality_score import QualityScoreCalculator
from edqi.calculators.quality_grade import QualityGradeCalculator

class DimensionAnalyzersTestCase(TestCase):
    def setUp(self):
        self.rules = {
            "required_fields": ["employee_id", "email", "department"],
            "email_regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            "phone_regex": "^\\+?1?\\d{9,15}$",
            "salary_min": 0,
            "timeliness_days": 365,
            "country_currency_map": {"India": "INR", "USA": "USD"},
            "quality_weights": {
                "completeness": 0.30,
                "validity": 0.25,
                "consistency": 0.20,
                "uniqueness": 0.15,
                "timeliness": 0.10
            },
            "grade_boundaries": {
                "A+": [95.0, 100.0],
                "A": [90.0, 94.99],
                "B": [80.0, 89.99],
                "C": [70.0, 79.99],
                "D": [60.0, 69.99],
                "F": [0.0, 59.99]
            }
        }
        self.mock_context = type("MockContext", (object,), {
            "duplicate_employee_ids": {"101"},
            "duplicate_emails": {"dup@company.com"}
        })()

    def test_completeness_analyzer(self):
        analyzer = CompletenessAnalyzer()
        # All present
        record_clean = {"employee_id": "1", "email": "a@b.com", "department": "HR"}
        res = analyzer.analyze(record_clean, self.rules, self.mock_context)
        self.assertEqual(res.score, 100.0)
        self.assertEqual(len(res.issues), 0)

        # Missing email and department
        record_dirty = {"employee_id": "1", "email": None}
        res2 = analyzer.analyze(record_dirty, self.rules, self.mock_context)
        self.assertEqual(res2.score, 33.33) # 2/3 fields missing
        self.assertEqual(len(res2.issues), 2)
        self.assertEqual(res2.issues[0]["issue_type"], "MISSING_FIELD")

    def test_validity_analyzer(self):
        analyzer = ValidityAnalyzer()
        # Invalid email and negative salary
        record = {
            "email": "invalid_email_format",
            "phone": "+123456789012",
            "salary": "-5000"
        }
        res = analyzer.analyze(record, self.rules, self.mock_context)
        # 2 violations (email invalid, salary negative)
        self.assertEqual(res.score, 60.0) # 100 - 2 * 20
        self.assertEqual(len(res.issues), 2)

    def test_consistency_analyzer(self):
        analyzer = ConsistencyAnalyzer()
        # Dates timeline mismatch and Country mismatch
        record = {
            "joining_date": "2026-12-31",
            "exit_date": "2026-01-01",
            "country": "India",
            "currency": "USD"
        }
        res = analyzer.analyze(record, self.rules, self.mock_context)
        # 2 violations (dates inconsistent, currency inconsistent)
        self.assertEqual(res.score, 50.0) # 100 - 2 * 25
        self.assertEqual(len(res.issues), 2)

    def test_uniqueness_analyzer(self):
        analyzer = UniquenessAnalyzer()
        # Duplicate record key matches
        record_dup = {"employee_id": "101", "email": "dup@company.com"}
        res = analyzer.analyze(record_dup, self.rules, self.mock_context)
        self.assertEqual(res.score, 0.0) # duplicate is found
        self.assertEqual(len(res.issues), 2)

    def test_timeliness_analyzer(self):
        analyzer = TimelinessAnalyzer()
        # Valid fresh record
        record_fresh = {"updated_at": "2026-08-04 12:00:00"}
        res = analyzer.analyze(record_fresh, self.rules, self.mock_context)
        self.assertEqual(res.score, 100.0)

    def test_quality_scoring_calculator(self):
        dim_scores = {
            DataQualityDimension.COMPLETENESS.value: 100.0,
            DataQualityDimension.VALIDITY.value: 80.0,
            DataQualityDimension.CONSISTENCY.value: 100.0,
            DataQualityDimension.UNIQUENESS.value: 100.0,
            DataQualityDimension.TIMELINESS.value: 100.0
        }
        # Expected: 100*0.30 + 80*0.25 + 100*0.20 + 100*0.15 + 100*0.10 = 30 + 20 + 20 + 15 + 10 = 95.0
        score = QualityScoreCalculator.calculate_score(dim_scores, self.rules)
        self.assertEqual(score, 95.0)

        # Grade check
        grade = QualityGradeCalculator.calculate_grade(score, self.rules)
        self.assertEqual(grade, "A+")
