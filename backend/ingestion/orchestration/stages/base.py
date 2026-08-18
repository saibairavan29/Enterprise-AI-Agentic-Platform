from abc import ABC, abstractmethod
from ..pipeline.pipeline_context import PipelineContext

class BaseStage(ABC):
    """
    Abstract Base Class defining the standard stage execution contract.
    """
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def execute(self, context: PipelineContext) -> dict:
        """
        Executes standard stage task on the pipeline context object.
        Returns:
            dict containing:
                "status": "SUCCESS" | "FAILED" | "SKIPPED"
                "warnings": list
                "errors": list
                "output": dict
        """
        pass
