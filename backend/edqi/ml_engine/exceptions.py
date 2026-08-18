class MLEngineException(Exception):
    """Base exception class for all ML Engine operations."""
    pass

class DatasetBuilderException(MLEngineException):
    """Raised when errors occur during dataset compilation or features schema validations."""
    pass

class TrainingException(MLEngineException):
    """Raised when model training or fitting failures occur."""
    pass

class PredictionException(MLEngineException):
    """Raised when inference pipelines or predictions validation fail."""
    pass

class EvaluationException(MLEngineException):
    """Raised when scoring evaluation computations encounter errors."""
    pass

class ModelRepositoryException(MLEngineException):
    """Raised when loading or saving joblib/metadata files fails."""
    pass

class ConfigurationException(MLEngineException):
    """Raised when parameters or weights are incorrectly parsed from configurations."""
    pass
