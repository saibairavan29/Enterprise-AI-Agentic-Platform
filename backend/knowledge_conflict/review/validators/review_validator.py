from ...exceptions.exceptions import ValidationException

class ReviewValidator:
    """
    Validates user groups role permission checks and review payload variables.
    """
    @staticmethod
    def validate_reviewer_permissions(user):
        """Ensures the operating user belongs to Analyst or Admin user groups."""
        if not user:
            raise ValidationException("Review user session cannot be empty.")
            
        role = getattr(user, 'role', 'reader').lower()
        if role not in ['admin', 'analyst']:
            raise ValidationException("Operation rejected: user does not hold review permissions roles.")

    @staticmethod
    def validate_review_payload(data: dict):
        status = data.get("review_status")
        if status and status not in ['PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'RESOLVED']:
            raise ValidationException(f"Invalid review status: '{status}'")
            
        decision = data.get("decision")
        if decision and decision not in ['CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_MORE_REVIEW']:
            raise ValidationException(f"Invalid decision code: '{decision}'")
            
        resolution = data.get("resolution")
        if resolution and resolution not in ['KEEP_SOURCE', 'KEEP_TARGET', 'MERGE', 'MANUAL_EDIT', 'IGNORE']:
            raise ValidationException(f"Invalid resolution code: '{resolution}'")
