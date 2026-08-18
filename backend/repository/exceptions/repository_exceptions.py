class RepositoryException(Exception):
    """Base exception for all repository operations."""
    pass

class ValidationException(RepositoryException):
    """Raised when repository payload validation fails."""
    pass

class SyncException(RepositoryException):
    """Raised when synchronization pipeline fails."""
    pass

class NotFoundException(RepositoryException):
    """Raised when request document or record doesn't exist."""
    pass
