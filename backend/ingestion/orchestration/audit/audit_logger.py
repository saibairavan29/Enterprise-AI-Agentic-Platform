import logging

logger = logging.getLogger('audit')

class AuditLogger:
    """
    Logger utility enforcing the correlation-id formatting tags across the pipeline.
    """
    @staticmethod
    def log_event(pipeline_id, doc_id, user_id, stage, message, level="info"):
        prefix = f"[Pipeline: {pipeline_id} | Doc: {doc_id} | User: {user_id} | Stage: {stage}]"
        if level == "error":
            logger.error(f"{prefix} {message}")
        else:
            logger.info(f"{prefix} {message}")
