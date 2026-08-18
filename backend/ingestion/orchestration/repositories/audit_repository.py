import logging
import json
from datetime import datetime

# Get audit-specific logger instance
logger = logging.getLogger('audit')

class AuditRepository:
    """
    Repository responsible for persisting structured audit logs.
    Ensures zero enterprise data leakage by logging only execution metrics and counts.
    """
    def log_audit(self, pipeline_id, document_id, user_id, start_time, end_time, duration, status, warnings, errors):
        """
        Serializes and logs ingestion audit trace records.
        """
        audit_record = {
            "pipeline_id": pipeline_id,
            "document_id": document_id,
            "user_id": user_id,
            "start_time": start_time.isoformat() if isinstance(start_time, datetime) else str(start_time),
            "end_time": end_time.isoformat() if isinstance(end_time, datetime) else str(end_time),
            "execution_duration": duration,
            "status": status,
            "warnings_count": len(warnings),
            "errors_count": len(errors),
            "warnings": warnings,
            "errors": errors
        }
        # Log serialized audit record
        logger.info(json.dumps(audit_record))
        return audit_record
