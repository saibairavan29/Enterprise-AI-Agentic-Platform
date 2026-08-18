from django.test import TestCase
from ..classifiers.classifiers import (
    DuplicateClassifier,
    ConflictClassifier,
    OutdatedClassifier,
    ConsistencyClassifier,
    ClassifierRegistry
)

class MockCandidate:
    def __init__(self, strategy, source_text, target_text, metadata=None):
        self.strategy_used = strategy
        self.source_text = source_text
        self.target_text = target_text
        self.metadata = metadata or {}


class ClassifiersTests(TestCase):
    """
    Test suite validating independent classifiers logic against
    configured thresholds and evidence lists.
    """
    def setUp(self):
        self.config = {
            "similarity_threshold_duplicate": 0.92,
            "similarity_threshold_consistent": 0.70,
            "contradiction_keywords": ["not", "except", "increased", "decreased"]
        }

    def test_duplicate_classifier_trigger(self):
        classifier = DuplicateClassifier(self.config)
        cand = MockCandidate("SameTitleStrategy", "Rule active.", "Rule active.")
        
        # Above duplicate threshold
        res = classifier.classify(cand, {"overall_similarity": 0.95}, {})
        self.assertIsNotNone(res)
        self.assertEqual(res["conflict_type"], "DUPLICATE")
        self.assertEqual(res["severity"], "LOW")
        
        # Below duplicate threshold
        res_fail = classifier.classify(cand, {"overall_similarity": 0.85}, {})
        self.assertIsNone(res_fail)

    def test_conflict_classifier_with_contradiction_evidence(self):
        classifier = ConflictClassifier(self.config)
        cand = MockCandidate("SameTitleStrategy", "Rate increased.", "Rate decreased.")
        
        # Similarity is high, but evidence has contradiction terms
        res = classifier.classify(
            cand, 
            {"overall_similarity": 0.80}, 
            {"contradiction_terms": ["increased", "decreased"]}
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["conflict_type"], "CONFLICTING")
        self.assertEqual(res["severity"], "HIGH")

    def test_conflict_classifier_with_numerical_mismatch(self):
        classifier = ConflictClassifier(self.config)
        cand = MockCandidate("SimilarityWindowStrategy", "Salary is 5000", "Salary is 5500")
        
        # Similarity is high, but evidence shows numeric mismatch difference
        res = classifier.classify(
            cand, 
            {"overall_similarity": 0.85}, 
            {"numeric_difference": 500.0}
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["conflict_type"], "CONFLICTING")
        self.assertEqual(res["severity"], "CRITICAL")

    def test_outdated_classifier_timeline(self):
        classifier = OutdatedClassifier(self.config)
        cand = MockCandidate("SameVersionStrategy", "Content A", "Content B")
        
        # Candidate has version gap evidence
        res = classifier.classify(cand, {"overall_similarity": 0.80}, {"version_difference": 2})
        self.assertIsNotNone(res)
        self.assertEqual(res["conflict_type"], "OUTDATED")
        self.assertEqual(res["severity"], "MEDIUM")

    def test_consistency_classifier_trigger(self):
        classifier = ConsistencyClassifier(self.config)
        cand = MockCandidate("SameTitleStrategy", "Text A", "Text A variant")
        
        # Similar, but has no version gap, no contradiction terms, and no numeric diff
        res = classifier.classify(
            cand, 
            {"overall_similarity": 0.88}, 
            {"contradiction_terms": [], "numeric_difference": 0.0, "version_difference": 0}
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["conflict_type"], "CONSISTENT")
        self.assertEqual(res["severity"], "LOW")
        
    def test_classifier_registry_priorities(self):
        active = ClassifierRegistry.get_active_classifiers(self.config)
        
        # Should instantiate 4 classifiers
        self.assertEqual(len(active), 4)
        
        # Verify order priority (Conflict first, Consistent last)
        self.assertEqual(active[0].__class__.__name__, "ConflictClassifier")
        self.assertEqual(active[3].__class__.__name__, "ConsistencyClassifier")
class_names = [c.__class__.__name__ for c in active]
        self.assertIn("DuplicateClassifier", class_names)
        self.assertIn("OutdatedClassifier", class_names)
