import os
import json
import logging
from ...exceptions.exceptions import ValidationException

logger = logging.getLogger('enterprise')

class RulesLoader:
    """
    Singleton rules loader loading, parsing, and caching rules from conflict_rules.json.
    """
    _config = None

    @classmethod
    def load_rules(cls) -> dict:
        if cls._config is not None:
            return cls._config
            
        # Resolve config path next to loader
        dir_path = os.path.dirname(os.path.abspath(__file__))
        rules_path = os.path.join(dir_path, "conflict_rules.json")
        
        if not os.path.exists(rules_path):
            logger.warning(f"conflict_rules.json not found at {rules_path}. Loading defaults.")
            return cls._get_defaults()
            
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                cls._config = json.load(f)
            logger.info("Successfully loaded conflict detection configurations.")
            return cls._config
        except Exception as e:
            raise ValidationException(f"Failed to load conflict_rules.json: {str(e)}")

    @classmethod
    def reset_rules(cls):
        cls._config = None

    @classmethod
    def _get_defaults(cls) -> dict:
        return {
            "embedding_model": "MiniLMEmbedding",
            "similarity_threshold_duplicate": 0.92,
            "similarity_threshold_consistent": 0.70,
            "outdated_version_gap": 1,
            "minimum_sentence_length": 5,
            "contradiction_keywords": ["not", "except", "increased", "decreased", "higher", "lower"]
        }
