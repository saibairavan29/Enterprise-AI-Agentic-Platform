import logging
from ..exceptions.exceptions import ClassificationException

logger = logging.getLogger('enterprise')

class BaseClassifier:
    """
    Abstract Base Class for candidate pair classifiers.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}

    def classify(self, candidate, similarity_report: dict, evidence: dict) -> dict:
        """
        Evaluate candidate and similarity report.
        Returns a standardized dictionary if matching constraints are met, else None:
        {
            "conflict_type": str,
            "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "confidence": float,
            "explanation": str,
            "evidence": dict
        }
        """
        pass


class DuplicateClassifier(BaseClassifier):
    """
    Classifies highly similar texts as DUPLICATE.
    """
    def classify(self, candidate, similarity_report: dict, evidence: dict) -> dict:
        threshold = self.config.get("similarity_threshold_duplicate", 0.95)
        sim = similarity_report.get("overall_similarity", 0.0)
        
        if sim >= threshold:
            return {
                "conflict_type": "DUPLICATE",
                "severity": "LOW",
                "confidence": round(sim, 4),
                "explanation": f"Texts match exactly or are highly similar (similarity: {sim:.2f} >= threshold: {threshold:.2f}).",
                "evidence": evidence
            }
        return None


class ConflictClassifier(BaseClassifier):
    """
    Identifies semantic contradictions or numerical mismatches in records.
    """
    def classify(self, candidate, similarity_report: dict, evidence: dict) -> dict:
        threshold = self.config.get("similarity_threshold_consistent", 0.70)
        sim = similarity_report.get("overall_similarity", 0.0)
        
        # Check if similarity is high, but we have contradiction terms or value/property differences
        has_contradiction = len(evidence.get("contradiction_terms", [])) > 0
        has_numeric_diff = evidence.get("numeric_difference", 0.0) > 0.0
        prop_diffs = evidence.get("property_differences", [])
        has_prop_diff = len(prop_diffs) > 0
        
        if sim >= threshold and (has_contradiction or has_numeric_diff or has_prop_diff):
            severity = "HIGH"
            explanation = "Semantic text contradictions identified."
            
            if has_prop_diff:
                explanation = f"Conflicting property values detected for: {', '.join(prop_diffs)}."
            if has_numeric_diff:
                severity = "CRITICAL"
                explanation = f"Numerical value mismatch detected (difference: {evidence['numeric_difference']})."
                
            return {
                "conflict_type": "CONFLICTING",
                "severity": severity,
                "confidence": round(sim, 4),
                "explanation": explanation,
                "evidence": evidence
            }
        return None


class OutdatedClassifier(BaseClassifier):
    """
    Identifies older versions of documents or timeline date sequence gaps as OUTDATED / TIMELINE_CONFLICT.
    """
    def classify(self, candidate, similarity_report: dict, evidence: dict) -> dict:
        version_gap = evidence.get("version_difference", 0)
        date_gap = evidence.get("date_difference_days", 0)
        has_timeline_conflict = evidence.get("timeline_conflict", False)
        
        if (candidate.strategy_used == "SameVersionStrategy" and version_gap > 0) or (has_timeline_conflict and date_gap > 0):
            if has_timeline_conflict:
                explanation = evidence.get("timeline_details") or f"Timeline date sequence mismatch detected ({date_gap} days gap)."
                severity = "HIGH"
            else:
                explanation = f"Source segment belongs to an older document version (version difference: {version_gap})."
                severity = "MEDIUM"

            return {
                "conflict_type": "OUTDATED",
                "severity": severity,
                "confidence": 0.95,
                "explanation": explanation,
                "evidence": evidence
            }
        return None


class ConsistencyClassifier(BaseClassifier):
    """
    Classifies similar, non-contradictory texts as CONSISTENT.
    """
    def classify(self, candidate, similarity_report: dict, evidence: dict) -> dict:
        threshold = self.config.get("similarity_threshold_consistent", 0.70)
        sim = similarity_report.get("overall_similarity", 0.0)
        
        # If similar but has no version gap, no contradiction terms, no property diffs, and no numeric diff
        has_contradiction = len(evidence.get("contradiction_terms", [])) > 0
        has_numeric_diff = evidence.get("numeric_difference", 0.0) > 0.0
        has_prop_diff = len(evidence.get("property_differences", [])) > 0
        version_gap = evidence.get("version_difference", 0)
        
        if sim >= threshold and not has_contradiction and not has_numeric_diff and not has_prop_diff and version_gap == 0:
            return {
                "conflict_type": "CONSISTENT",
                "severity": "LOW",
                "confidence": round(sim, 4),
                "explanation": f"Information is consistent across documents (similarity: {sim:.2f}).",
                "evidence": evidence
            }
        return None


class ClassifierRegistry:
    """
    Registry for managing and executing active conflict classifiers.
    """
    _registry = {}

    @classmethod
    def register(cls, name: str, classifier_class):
        cls._registry[name] = classifier_class
        logger.info(f"Registered conflict classifier: {name}")

    @classmethod
    def get_active_classifiers(cls, rules_config: dict) -> list:
        active = []
        # Classifiers are run in priority order (e.g. Conflict first, then Outdated, Duplicate, Consistent)
        order = ["ConflictClassifier", "OutdatedClassifier", "DuplicateClassifier", "ConsistencyClassifier"]
        
        for name in order:
            if name in cls._registry:
                classifier_class = cls._registry[name]
                active.append(classifier_class(rules_config))
                
        return active

# Register classifiers
ClassifierRegistry.register("DuplicateClassifier", DuplicateClassifier)
ClassifierRegistry.register("ConflictClassifier", ConflictClassifier)
ClassifierRegistry.register("OutdatedClassifier", OutdatedClassifier)
ClassifierRegistry.register("ConsistencyClassifier", ConsistencyClassifier)
