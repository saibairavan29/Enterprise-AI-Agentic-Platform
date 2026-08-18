import abc
import time

class AnalyzerResult:
    """
    Unified return object representing data quality dimension validation details.
    """
    def __init__(self, score: float, issues=None, recommendations=None, execution_time=0.0, metadata=None):
        self.score = score
        self.issues = issues or [] # list of dict issues
        self.recommendations = recommendations or [] # list of dict recommendations
        self.execution_time = execution_time
        self.metadata = metadata or {}


class BaseAnalyzer(abc.ABC):
    """
    Abstract base class for all rules-driven dimension analyzers.
    """
    def __init__(self, dimension_name: str):
        self.dimension_name = dimension_name

    @abc.abstractmethod
    def analyze(self, record: dict, rules: dict, context) -> AnalyzerResult:
        """
        Executes rules verification logic.
        Returns AnalyzerResult.
        """
        pass
