import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """
    Translates detected data quality anomalies into actionable suggested fixes
    with calculated confidence parameters.
    """
    @classmethod
    def generate_recommendation(cls, issue_type: str, field_name: str) -> tuple:
        """
        Deduces a suggested fix and a confidence float (0.0 to 1.0) based on issue parameters.
        Returns a tuple: (suggested_fix, confidence)
        """
        issue_type_upper = str(issue_type).upper()
        field_lower = str(field_name).lower()

        if issue_type_upper == "MISSING_FIELD":
            return f"Provide a valid value for the missing required field: '{field_name}'.", 0.90
        
        if issue_type_upper == "INVALID_FORMAT":
            if "email" in field_lower:
                return "Provide a valid format email address (e.g. user@enterprise.com).", 0.98
            if "phone" in field_lower:
                return "Provide a valid formatted phone number (e.g. +1234567890).", 0.95
            return f"Format of the field '{field_name}' is invalid according to formatting rules.", 0.85
            
        if issue_type_upper == "INVALID_RANGE":
            if "salary" in field_lower:
                return "Salary must be a non-negative amount greater than or equal to zero.", 0.99
            return f"Value in field '{field_name}' lies outside of configured rule range boundary.", 0.90

        if issue_type_upper == "INCONSISTENT_CROSS_FIELDS":
            if "date" in field_lower or "exit" in field_lower or "joining" in field_lower:
                return "Ensure joining date strictly precedes the exit date for this employee record.", 0.99
            if "currency" in field_lower or "country" in field_lower:
                return "Reconcile currency code matching the country of the record.", 0.95
            return f"Ensure values for related fields are consistent with standard business validation rules.", 0.80

        if issue_type_upper == "DUPLICATE_RECORD":
            return f"Verify duplicate record presence matching the unique field '{field_name}'; merge or purge the duplicate.", 0.95

        if issue_type_upper == "OUTDATED_RECORD":
            return "This record has not been updated within the timeliness threshold. Verify status and update.", 0.80

        # Generic fallback
        return f"Review field '{field_name}' value and format; reconcile details.", 0.70
