import logging
from datetime import datetime
from django.db import transaction

from ..models import ConflictReview
from ..workflows.review_workflow import ReviewWorkflow
from ..audit.audit_logger import ConflictAuditLogger
from ..notifications.notification_service import NotificationService
from .resolution_service import ResolutionService
from ...repositories.candidate_repository import CandidateRepository
from ..repositories.review_repository import ReviewRepository
from ...detection.repositories.conflict_repository import ConflictRepository
from ..validators.review_validator import ReviewValidator

logger = logging.getLogger('enterprise')

class ReviewService:
    """
    Service layer coordinating conflict reviews, state changes, auditing,
    and notifications.
    """
    def __init__(self):
        self.review_repo = ReviewRepository()
        self.conflict_repo = ConflictRepository()
        self.resolution_service = ResolutionService()

    def start_review(self, conflict_id, user) -> ConflictReview:
        ReviewValidator.validate_reviewer_permissions(user)
        
        conflict = self.conflict_repo.get_by_id(conflict_id)
        if not conflict:
            raise ValueError("Conflict record does not exist.")
            
        with transaction.atomic():
            # Check if a review already exists
            review = self.review_repo.get_by_conflict_id(conflict_id)
            
            if not review:
                # Create a new review
                review = self.review_repo.create_review(
                    conflict=conflict,
                    reviewer=user,
                    review_status='UNDER_REVIEW'
                )
                
                # Update conflict status to PROCESSING
                conflict.status = 'PROCESSING'
                conflict.save(update_fields=['status'])

                # Log audit trail
                ConflictAuditLogger.log_action(
                    conflict=conflict,
                    user=user,
                    action="Human review cycle initiated.",
                    action_type="REVIEW_STARTED",
                    old_status="NEW",
                    new_status="PROCESSING",
                    comments="Analyst opened conflict for evaluation."
                )
            elif review.review_status == 'PENDING':
                review.review_status = 'UNDER_REVIEW'
                review.reviewer = user
                self.review_repo.save_review(review)
                
                # Update conflict status to PROCESSING
                conflict.status = 'PROCESSING'
                conflict.save(update_fields=['status'])

                # Log audit trail
                ConflictAuditLogger.log_action(
                    conflict=conflict,
                    user=user,
                    action="Human review cycle initiated.",
                    action_type="REVIEW_STARTED",
                    old_status="PENDING",
                    new_status="PROCESSING",
                    comments="Analyst opened pending conflict for evaluation."
                )
            
            NotificationService.notify_review_created(str(review.review_id), str(conflict.conflict_id), user.username)
            return review

    def submit_decision(self, review_id, decision: str, status: str, comments: str, user) -> ConflictReview:
        ReviewValidator.validate_reviewer_permissions(user)
        
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise ValueError("Conflict review does not exist.")
            
        old_review_status = review.review_status
        old_conflict_status = review.conflict.status
        
        # Validate transitions
        ReviewWorkflow.validate_transition(old_review_status, status)
        ReviewValidator.validate_review_payload({"review_status": status, "decision": decision})
        
        with transaction.atomic():
            review.review_status = status
            review.decision = decision
            review.comments = comments
            review.reviewed_at = datetime.utcnow()
            self.review_repo.save_review(review)
            
            # Map review status to conflict status
            new_conflict_status = 'REVIEW_PENDING'
            if status == 'APPROVED':
                new_conflict_status = 'REVIEW_PENDING'
            elif status == 'REJECTED':
                new_conflict_status = 'REJECTED'
                
            review.conflict.status = new_conflict_status
            review.conflict.save(update_fields=['status'])
            
            # Log audit
            ConflictAuditLogger.log_action(
                conflict=review.conflict,
                user=user,
                action=f"Analyst decision submitted: {decision}.",
                action_type="DECISION_CONFIRMED",
                old_status=old_conflict_status,
                new_status=new_conflict_status,
                comments=comments
            )
            
            NotificationService.notify_review_completed(str(review.review_id), str(review.conflict.conflict_id), decision, status)
            
        return review

    def execute_resolution(self, review_id, resolution_type: str, user, custom_edit_data: dict = None):
        ReviewValidator.validate_reviewer_permissions(user)
        
        review = self.review_repo.get_by_id(review_id)
        if not review:
            raise ValueError("Conflict review does not exist.")
            
        old_review_status = review.review_status
        old_conflict_status = review.conflict.status
        
        # Can only resolve if approved or under review
        if old_review_status not in ['APPROVED', 'UNDER_REVIEW']:
            raise ValueError(f"Cannot resolve conflict in review status state '{old_review_status}'.")
            
        ReviewValidator.validate_review_payload({"resolution": resolution_type})
        
        with transaction.atomic():
            # Run repository modification logic
            result = self.resolution_service.resolve_conflict(
                conflict=review.conflict,
                resolution_type=resolution_type,
                user=user,
                review_id=review.review_id,
                custom_edit_data=custom_edit_data
            )
            
            # transition state to RESOLVED
            review.resolution = resolution_type
            review.review_status = 'RESOLVED'
            self.review_repo.save_review(review)
            
            # Update conflict status to VERIFIED
            review.conflict.status = 'VERIFIED'
            review.conflict.save(update_fields=['status'])
            
            # Log audit
            action_type_map = {
                'MERGE': 'MERGED',
                'MANUAL_EDIT': 'MANUAL_EDIT',
                'IGNORE': 'IGNORE',
                'KEEP_SOURCE': 'DECISION_CONFIRMED',
                'KEEP_TARGET': 'DECISION_CONFIRMED'
            }
            
            ConflictAuditLogger.log_action(
                conflict=review.conflict,
                user=user,
                action=f"Conflict resolved using method: {resolution_type}.",
                action_type=action_type_map.get(resolution_type, 'MERGED'),
                old_status=old_conflict_status,
                new_status="VERIFIED",
                comments=f"Resolution details DTO status: {result.status}."
            )
            
            return result
            
    def archive_conflict(self, conflict_id, user):
        ReviewValidator.validate_reviewer_permissions(user)
        conflict = self.conflict_repo.get_by_id(conflict_id)
        if not conflict:
            raise ValueError("Conflict does not exist.")
            
        old_status = conflict.status
        with transaction.atomic():
            conflict.status = 'ARCHIVED'
            conflict.save(update_fields=['status'])
            
            # Also update review status if present
            review = self.review_repo.get_by_conflict_id(conflict_id)
            if review:
                review.review_status = 'ARCHIVED'
                self.review_repo.save_review(review)
                
            ConflictAuditLogger.log_action(
                conflict=conflict,
                user=user,
                action="Archived conflict entries.",
                action_type="ARCHIVED",
                old_status=old_status,
                new_status="ARCHIVED",
                comments="Analyst archived the conflict context."
            )
