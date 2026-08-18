class StandardizationException(Exception):
    """
    Base exception class for all standardization engine errors.
    """
    pass

class StandardizationValidationException(StandardizationException):
    """
    Raised when standardized record fails type constraints or validation checks.
    """
    pass
