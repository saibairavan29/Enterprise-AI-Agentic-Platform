import logging
from edqi.analyzers.completeness_analyzer import CompletenessAnalyzer
from edqi.analyzers.validity_analyzer import ValidityAnalyzer
from edqi.analyzers.consistency_analyzer import ConsistencyAnalyzer
from edqi.analyzers.uniqueness_analyzer import UniquenessAnalyzer
from edqi.analyzers.timeliness_analyzer import TimelinessAnalyzer

logger = logging.getLogger(__name__)

# Map string configuration tags to active analyzer class objects
ANALYZER_MAP = {
    "Completeness": CompletenessAnalyzer,
    "Validity": ValidityAnalyzer,
    "Consistency": ConsistencyAnalyzer,
    "Uniqueness": UniquenessAnalyzer,
    "Timeliness": TimelinessAnalyzer
}

class AnalyzerRegistry:
    """
    Registry that dynamically returns instantiation lists of active dimension analyzers
    configured in rules properties.
    """
    @classmethod
    def get_enabled_analyzers(cls, rules: dict) -> list:
        """
        Instantiates and returns list of analyzers enabled in rules config.
        """
        enabled_tags = rules.get("enabled_analyzers", [
            "Completeness",
            "Validity",
            "Consistency",
            "Uniqueness",
            "Timeliness"
        ])
        
        analyzers_list = []
        for tag in enabled_tags:
            cls_obj = ANALYZER_MAP.get(tag)
            if cls_obj:
                analyzers_list.append(cls_obj())
                logger.debug(f"Instantiated and registered quality analyzer: {tag}")
            else:
                logger.warning(f"Configured analyzer '{tag}' is not registered in ANALYZER_MAP.")
                
        return analyzers_list
