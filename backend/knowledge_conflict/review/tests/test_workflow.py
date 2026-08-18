from django.test import TestCase
from ...exceptions.exceptions import ValidationException
from ..workflows.review_workflow import ReviewWorkflow

class WorkflowTests(TestCase):
    """
    Test suite validating workflow engine status transitions bounds.
    """
    def test_valid_transitions_pass(self):
        # PENDING -> UNDER_REVIEW should be allowed
        ReviewWorkflow.validate_transition('PENDING', 'UNDER_REVIEW')
        
        # UNDER_REVIEW -> APPROVED should be allowed
        ReviewWorkflow.validate_transition('UNDER_REVIEW', 'APPROVED')
        
        # APPROVED -> RESOLVED should be allowed
        ReviewWorkflow.validate_transition('APPROVED', 'RESOLVED')
        
        # Transitioning to the same status is implicitly allowed (noop)
        ReviewWorkflow.validate_transition('PENDING', 'PENDING')

    def test_invalid_transitions_raise(self):
        # Cannot transition from PENDING directly to RESOLVED without approval
        with self.assertRaises(ValidationException):
            ReviewWorkflow.validate_transition('PENDING', 'RESOLVED')
            
        # Cannot transition from RESOLVED back to UNDER_REVIEW
        with self.assertRaises(ValidationException):
            ReviewWorkflow.validate_transition('RESOLVED', 'UNDER_REVIEW')
            
        # Cannot transition from ARCHIVED to UNDER_REVIEW
        with self.assertRaises(ValidationException):
            ReviewWorkflow.validate_transition('ARCHIVED', 'UNDER_REVIEW')
