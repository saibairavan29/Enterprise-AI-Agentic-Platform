class AuditBuilder:
    """
    Builder responsible for assembling pipeline audits.
    """
    def build_event(self, pipeline_id, doc_id, user_id, stage_name, status, duration, message):
        """Assembles standard correlation audit entries."""
        return {
            "pipeline_id": pipeline_id,
            "document_id": doc_id,
            "user_id": user_id,
            "stage": stage_name,
            "status": status,
            "duration": duration,
            "message": message
        }
