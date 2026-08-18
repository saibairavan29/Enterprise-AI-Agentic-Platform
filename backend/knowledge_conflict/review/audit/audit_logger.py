import logging
from ..models import ConflictAuditHistory

logger = logging.getLogger('enterprise')

class ConflictAuditLogger:
    """
    Service helper that creates immutable records in ConflictAuditHistory
    for human review actions, ensuring auditable traceability.
    """
    @staticmethod
    def log_action(conflict, user, action: str, action_type: str, 
                   old_status: str, new_status: str, comments: str = "") -> ConflictAuditHistory:
        try:
            entry = ConflictAuditHistory.objects.create(
                conflict=conflict,
                user=user,
                action=action,
                action_type=action_type,
                old_status=old_status,
                new_status=new_status,
                comments=comments
            )
            logger.info(f"[Audit Log] Conflict {str(conflict.conflict_id)[:8]} updated to {new_status} by {user} (Action: {action_type})")
            return entry
        except Exception as e:
            logger.error(f"Audit logging failed for conflict {conflict.conflict_id}: {str(e)}", exc_info=True)
            return None
