from ingestion.models import ProcessingHistory, Document

class ProcessingRepository:
    """
    Repository responsible for persisting pipeline runs and stages performance history records.
    """
    def create_history(self, pipeline_id, document_id, stage_name, stage_status, start_time, end_time, duration, retry_count, warnings_count, errors_count):
        """
        Creates and stores a ProcessingHistory record in PostgreSQL.
        """
        return ProcessingHistory.objects.create(
            pipeline_id=pipeline_id,
            document_id=document_id,
            stage_name=stage_name,
            stage_status=stage_status,
            start_time=start_time,
            end_time=end_time,
            execution_duration=duration,
            retry_count=retry_count,
            warning_count=warnings_count,
            error_count=errors_count
        )
