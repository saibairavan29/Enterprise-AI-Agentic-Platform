from enum import Enum

class PipelineState(Enum):
    """
    State machine values tracking processing steps.
    """
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    PARSING = "PARSING"
    OCR_RUNNING = "OCR_RUNNING"
    METADATA_EXTRACTED = "METADATA_EXTRACTED"
    SCHEMA_MAPPED = "SCHEMA_MAPPED"
    STANDARDIZED = "STANDARDIZED"
    PERSISTING = "PERSISTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
