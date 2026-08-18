from ..exceptions.exceptions import ValidationException

class CandidateValidator:
    """
    Validation engine checks candidate payloads, configs, and repository inputs.
    """
    @staticmethod
    def validate_generation_inputs(documents: list, records: list):
        """Validates that loaded document and record datasets are iterable and non-empty."""
        if documents is None:
            raise ValidationException("Loaded documents collection list cannot be None.")
        if records is None:
            raise ValidationException("Loaded records collection list cannot be None.")

    @staticmethod
    def validate_rules_config(config: dict):
        """Validates the structure of configuration parameters."""
        if not isinstance(config, dict):
            raise ValidationException("Rules configuration must be a dictionary.")
            
        required_keys = ["window_size", "strategies"]
        for key in required_keys:
            if key not in config:
                raise ValidationException(f"Missing mandatory configuration key: '{key}'")
                
        # Ensure strategies sub-block is formatted correctly
        strategies = config.get("strategies", {})
        if not isinstance(strategies, dict):
            raise ValidationException("'strategies' configurations must be a sub-dictionary.")

    @staticmethod
    def validate_candidate_fields(candidate_data: dict):
        """Ensures generated candidates contain required database model keys."""
        required = [
            "source_document_id", "target_document_id",
            "source_segment_id", "target_segment_id",
            "source_text", "target_text",
            "strategy_used", "strategy_confidence"
        ]
        for field in required:
            val = candidate_data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                raise ValidationException(f"Candidate contains missing or blank field: '{field}'")
