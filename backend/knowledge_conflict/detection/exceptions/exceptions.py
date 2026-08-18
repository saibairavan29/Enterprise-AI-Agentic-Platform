from ...exceptions.exceptions import KnowledgeConflictException

class DetectionException(KnowledgeConflictException):
    """Base exception for all errors inside the conflict detection module."""
    pass

class EmbeddingException(DetectionException):
    """Raised when generating embeddings fails."""
    pass

class SimilarityException(DetectionException):
    """Raised when calculating cosine similarity scores fails."""
    pass

class EvidenceExtractionException(DetectionException):
    """Raised when extracting evidence features fails."""
    pass

class ClassificationException(DetectionException):
    """Raised when running classifiers fails."""
    pass
