class KnowledgeConflictException(Exception):
    """Base exception class for all errors in the knowledge_conflict package."""
    pass

class ExtractorException(KnowledgeConflictException):
    """Raised when text or field extraction from documents/records fails."""
    pass

class NormalizationException(KnowledgeConflictException):
    """Raised when text normalization stages fail."""
    pass

class SegmentationException(KnowledgeConflictException):
    """Raised when text segmentation or splitting fails."""
    pass

class CandidateGenerationException(KnowledgeConflictException):
    """Raised when candidate generation strategies fail."""
    pass

class ValidationException(KnowledgeConflictException):
    """Raised when configurations, schemas, or payload validation fails."""
    pass
