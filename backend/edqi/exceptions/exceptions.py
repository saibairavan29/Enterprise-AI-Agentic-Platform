class EDQIException(Exception):
    """Base exception for all EDQI operations."""
    pass

class QualityRulesError(EDQIException):
    """Exception raised when rules loading or schema validation fails."""
    pass

class AssessmentError(EDQIException):
    """Exception raised when record level quality assessment errors occur."""
    pass

class ProfilerError(EDQIException):
    """Exception raised when data profiling calculation fails."""
    pass
