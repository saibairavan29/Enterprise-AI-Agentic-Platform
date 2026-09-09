from ingestion.models import ProcessingHistory, Document

class ProcessingRepository:
    """
    Repository responsible for persisting pipeline runs and stages performance history records.
    """
    def create_history(self, pipeline_id, document_id, stage_name, stage_status, start_time, end_time, duration, retry_count, warnings_count, errors_count):
        """
        Creates or updates a ProcessingHistory record, ensuring deduplication.
        """
        return self.create_or_update_history(
            pipeline_id, document_id, stage_name, stage_status,
            start_time, end_time, duration, retry_count, warnings_count, errors_count
        )

    def create_or_update_history(self, pipeline_id, document_id, stage_name, stage_status, start_time, end_time, duration, retry_count, warnings_count, errors_count):
        """
        Safely updates or creates a ProcessingHistory record for real-time pipeline monitoring,
        handling and purging any duplicate entries if present.
        """
        existing_qs = ProcessingHistory.objects.filter(
            pipeline_id=pipeline_id,
            document_id=document_id,
            stage_name=stage_name
        ).order_by('id')

        defaults = {
            'stage_status': stage_status,
            'start_time': start_time,
            'end_time': end_time,
            'execution_duration': duration,
            'retry_count': retry_count,
            'warning_count': warnings_count,
            'error_count': errors_count
        }

        if existing_qs.exists():
            records = list(existing_qs)
            obj = records[0]
            for key, val in defaults.items():
                setattr(obj, key, val)
            obj.save()

            # Delete any duplicate history rows created by race conditions or legacy callers
            if len(records) > 1:
                dup_ids = [r.id for r in records[1:]]
                ProcessingHistory.objects.filter(id__in=dup_ids).delete()
            return obj
        else:
            return ProcessingHistory.objects.create(
                pipeline_id=pipeline_id,
                document_id=document_id,
                stage_name=stage_name,
                **defaults
            )
