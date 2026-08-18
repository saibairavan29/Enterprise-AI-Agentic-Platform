from ...exceptions.exceptions import ValidationException

class ConflictValidator:
    """
    Validation checks for conflict detection configurations and database payloads.
    """
    @staticmethod
    def validate_rules_config(config: dict):
        if not isinstance(config, dict):
            raise ValidationException("Conflict rules configuration must be a dictionary.")
            
        required_keys = ["embedding_model", "similarity_threshold_duplicate", "similarity_threshold_consistent"]
        for key in required_keys:
            if key not in config:
                raise ValidationException(f"Missing mandatory configuration key: '{key}'")

    @staticmethod
    def validate_conflict_fields(conflict_data: dict):
        required = [
            "conflict_type", "severity", "overall_similarity", "confidence_score",
            "embedding_model", "classifier_used"
        ]
        for field in required:
            val = conflict_data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise ValidationException(f"Conflict data missing required field: '{field}'")
