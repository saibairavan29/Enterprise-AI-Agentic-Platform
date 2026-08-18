import logging

logger = logging.getLogger('enterprise')

class NotificationService:
    """
    Stub notification service providing clean interfaces for downstream
    Slack, Teams, Email, or WebSocket notifications.
    """
    @staticmethod
    def notify_review_created(review_id: str, conflict_id: str, reviewer_name: str = "Unassigned"):
        """Trigger notification when a new human review is created/pending."""
        logger.info(f"[Notification Stub] Review {review_id} created for Conflict {conflict_id}. Assigned to: {reviewer_name}")

    @staticmethod
    def notify_review_completed(review_id: str, conflict_id: str, decision: str, resolution: str):
        """Trigger notification when a conflict review is resolved/completed."""
        logger.info(f"[Notification Stub] Review {review_id} completed. Decision: {decision}, Resolution: {resolution}")

    @staticmethod
    def notify_critical_conflict(conflict_id: str, source_doc: str, target_doc: str):
        """Trigger high-priority alert for critical severity conflict matches."""
        logger.warning(f"[Notification Stub] CRITICAL CONFLICT DETECTED! Conflict ID: {conflict_id}. Compares {source_doc} with {target_doc}")
