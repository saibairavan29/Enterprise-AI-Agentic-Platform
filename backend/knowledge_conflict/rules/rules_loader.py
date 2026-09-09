import os
import json
import logging
from ..exceptions.exceptions import ValidationException

logger = logging.getLogger('enterprise')

class RulesLoader:
    """
    Singleton rules loader loading, parsing, and caching rules from candidate_rules.json.
    """
    _config = None

    @classmethod
    def load_rules(cls) -> dict:
        if cls._config is not None:
            return cls._config
            
        # Get path of candidate_rules.json next to this python file
        dir_path = os.path.dirname(os.path.abspath(__file__))
        rules_path = os.path.join(dir_path, "candidate_rules.json")
        
        if not os.path.exists(rules_path):
            logger.warning(f"candidate_rules.json not found at {rules_path}. Using default configurations.")
            return cls._get_defaults()
            
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                cls._config = json.load(f)
            logger.info("Successfully loaded candidate generation configuration rules.")
            return cls._config
        except Exception as e:
            raise ValidationException(f"Failed to parse candidate_rules.json: {str(e)}")

    @classmethod
    def reset_rules(cls):
        """Reset the cached config (useful for testing)."""
        cls._config = None

    @classmethod
    def _get_defaults(cls) -> dict:
        return {
            "window_size": 1000,
            "department_matching": True,
            "title_similarity": True,
            "max_comparisons": 10000,
            "minimum_text_length": 5,
            "stop_words": [],
            "strategies": {
                "SameVersionStrategy": {"enabled": True, "confidence": 100},
                "SameEntityTypeStrategy": {"enabled": True, "confidence": 90},
                "SameDepartmentStrategy": {"enabled": True, "confidence": 90},
                "SameTitleStrategy": {"enabled": True, "confidence": 75},
                "SimilarityWindowStrategy": {
                    "enabled": True, 
                    "confidence": 60,
                    "numeric_fields": {
                        "salary": {"window": 1000.0}
                    }
                },
                "UniversalCrossCheckStrategy": {
                    "enabled": True,
                    "confidence": 85
                }
            }
        }
