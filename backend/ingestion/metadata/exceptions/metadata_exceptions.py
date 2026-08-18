class MetadataException(Exception):
    """
    Base exception class for all metadata engine errors.
    """
    pass

class MetadataExtractionException(MetadataException):
    """
    Raised when an error occurs during segment metadata extraction.
    """
    pass

class MetadataValidationException(MetadataException):
    """
    Raised when the compiled metadata payload violates schema validations.
    """
    pass
