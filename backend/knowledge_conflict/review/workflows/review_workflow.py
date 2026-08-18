from ...exceptions.exceptions import ValidationException

class ReviewWorkflow:
    """
    Workflow transition engine for human review stages.
    Validates state changes and raises ValidationException for illegal operations.
    """
    VALID_TRANSITIONS = {
        'PENDING': ['UNDER_REVIEW', 'APPROVED', 'REJECTED'],
        'UNDER_REVIEW': ['APPROVED', 'REJECTED', 'PENDING'],
        'APPROVED': ['RESOLVED', 'ARCHIVED'],
        'REJECTED': ['PENDING', 'ARCHIVED'],
        'RESOLVED': ['ARCHIVED'],
        'ARCHIVED': []
    }

    @classmethod
    def validate_transition(cls, old_status: str, new_status: str):
        if old_status == new_status:
            return
            
        allowed = cls.VALID_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            raise ValidationException(
                f"Invalid workflow state transition: cannot modify status from '{old_status}' to '{new_status}'."
            )
