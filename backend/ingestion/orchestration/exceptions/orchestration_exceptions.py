class OrchestrationException(Exception):
    """
    Base exception class for all pipeline orchestration errors.
    """
    pass

class StageExecutionException(OrchestrationException):
    """
    Raised when an individual stage execution fails.
    """
    def __init__(self, stage_name, message):
        self.stage_name = stage_name
        super().__init__(f"Stage '{stage_name}' failed: {message}")
