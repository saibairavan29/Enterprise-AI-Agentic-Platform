class ResponseBuilder:
    """
    Builder responsible for compiling the standardized orchestration final response.
    """
    def build_response(self, success, document_id, pipeline_id, processing_status, pipeline_duration, stage_execution, metadata, standardized_record, warnings=None, errors=None):
        """Compiles standard pipeline run results."""
        return {
            "success": success,
            "document_id": str(document_id) if document_id else "",
            "pipeline_id": pipeline_id or "",
            "processing_status": processing_status or "FAILED",
            "pipeline_duration": float(pipeline_duration) if pipeline_duration is not None else 0.0,
            "stage_execution": stage_execution or {},
            "metadata": metadata or {},
            "standardized_record": standardized_record or {},
            "warnings": warnings or [],
            "errors": errors or []
        }
