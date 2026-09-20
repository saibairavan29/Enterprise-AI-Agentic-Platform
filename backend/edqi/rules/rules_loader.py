import os
import json
import logging

logger = logging.getLogger(__name__)

# Default configurations in case reading from json fails
DEFAULT_RULES = {
  "enabled_analyzers": [
    "Completeness",
    "Validity",
    "Consistency",
    "Uniqueness",
    "Timeliness"
  ],
  "required_fields": [],
  "email_regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
  "phone_regex": "^\\+?1?\\d{9,15}$",
  "salary_min": 0,
  "timeliness_days": 365,
  "country_currency_map": {
    "India": "INR",
    "USA": "USD",
    "United States": "USD",
    "Germany": "EUR"
  },
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

class QualityRulesLoader:
    _cached_rules = None

    @classmethod
    def load_rules(cls) -> dict:
        """
        Loads rules dynamically from quality_rules.json. Returns a dictionary.
        """
        if cls._cached_rules is not None:
            return cls._cached_rules

        json_path = os.path.join(os.path.dirname(__file__), "quality_rules.json")
        if not os.path.exists(json_path):
            logger.warning(f"quality_rules.json was not found at {json_path}. Falling back to default rules.")
            return DEFAULT_RULES

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            cls._cached_rules = rules
            logger.info("Successfully loaded quality_rules.json configuration.")
            return rules
        except Exception as e:
            logger.error(f"Error loading quality_rules.json: {str(e)}. Falling back to default rules.")
            return DEFAULT_RULES

    @classmethod
    def clear_cache(cls):
        cls._cached_rules = None
