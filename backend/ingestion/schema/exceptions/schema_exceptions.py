class SchemaException(Exception):
    """
    Base exception class for all canonical schema mapping errors.
    """
    pass

class SchemaMappingException(SchemaException):
    """
    Raised when an error occurs during canonical fields mapping.
    """
    pass

class SchemaValidationException(SchemaException):
    """
    Raised when canonical validations fail.
    """
    pass
