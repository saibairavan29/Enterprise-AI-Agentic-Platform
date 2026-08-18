class PipelineResult:
    """
    Wrapper holding finalized pipeline execution metrics, reports, and payloads.
    """
    def __init__(self, success, document_id, pipeline_id, processing_status, pipeline_duration, stage_execution, metadata, standardized_record, warnings, errors):
        self.success = success
        self.document_id = document_id
        self.pipeline_id = pipeline_id
        self.processing_status = processing_status
        self.pipeline_duration = pipeline_duration
        self.stage_execution = stage_execution
        self.metadata = metadata
        self.standardized_record = standardized_record
        self.warnings = warnings or []
        self.errors = errors or []

    def to_dict(self):
        """Converts result object to clean JSON dictionary representation."""
        return {
            "success": self.success,
            "document_id": self.document_id,
            "pipeline_id": self.pipeline_id,
            "processing_status": self.processing_status,
            "pipeline_duration": self.pipeline_duration,
            "stage_execution": self.stage_execution,
            "metadata": self.metadata or {},
            "standardized_record": self.standardized_record or {},
            "warnings": self.warnings,
            "errors": self.errors
        }
