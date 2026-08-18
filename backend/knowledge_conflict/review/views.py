import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.exceptions import ObjectDoesNotExist

from ..models import KnowledgeConflict
from .models import ConflictReview, ConflictAuditHistory
from .serializers import ConflictSerializer, ReviewSerializer, AuditHistorySerializer
from .services.review_service import ReviewService
from ..detection.services.orchestration import ConflictDetectionOrchestrator
from .validators.review_validator import ReviewValidator

logger = logging.getLogger('enterprise')

class ConflictsBaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def handle_exception(self, exc):
        logger.error(f"API view exception raised: {str(exc)}", exc_info=True)
        return Response({
            "success": False,
            "errors": [str(exc)],
            "message": "Operation failed."
        }, status=status.HTTP_400_BAD_REQUEST)


class ConflictsListView(ConflictsBaseView):
    """
    GET: List all detected conflicts.
    POST: Triggers E2E conflict detection run dynamically.
    """
    def get(self, request):
        status_filter = request.query_params.get("status")
        queryset = KnowledgeConflict.objects.all().order_by('-detected_at')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        serializer = ConflictSerializer(queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Fetched conflicts list successfully."
        })

    def post(self, request):
        # Trigger E2E conflict detection orchestrator
        ReviewValidator.validate_reviewer_permissions(request.user)
        
        # Cleanup old unresolved candidates and conflicts
        from knowledge_conflict.models import KnowledgeCandidate
        from django.db import transaction
        with transaction.atomic():
            KnowledgeCandidate.objects.exclude(
                conflicts__status__in=['VERIFIED', 'REJECTED', 'ARCHIVED']
            ).delete()
        
        # 1. Generate comparison candidates from current repository state
        from knowledge_conflict.services.orchestration import CandidateOrchestrationService
        candidate_service = CandidateOrchestrationService()
        candidate_report = candidate_service.generate_candidates()
        
        # 2. Run conflict detection pipeline
        orchestrator = ConflictDetectionOrchestrator()
        report = orchestrator.run_detection()
        
        # Append candidates statistics
        report["candidates_generated"] = candidate_report.get("candidates_persisted", 0)
        
        return Response({
            "success": True,
            "data": report,
            "message": "Conflict detection pipeline executed successfully."
        })


class ConflictsStatisticsView(ConflictsBaseView):
    """
    GET: Compiles summary statistical metrics for the dashboard.
    """
    def get(self, request):
        conflicts = KnowledgeConflict.objects.all()
        total_count = conflicts.count()
        pending = conflicts.filter(status__in=['NEW', 'PROCESSING', 'REVIEW_PENDING']).count()
        critical = conflicts.filter(severity='CRITICAL').count()
        verified = conflicts.filter(status='VERIFIED').count()
        
        # Calculate average similarity score
        avg_sim = 0.0
        if total_count > 0:
            avg_sim = sum(c.overall_similarity for c in conflicts) / total_count
            
        return Response({
            "success": True,
            "data": {
                "total_conflicts": total_count,
                "pending_reviews": pending,
                "critical_conflicts": critical,
                "resolved_conflicts": verified,
                "average_similarity": round(avg_sim, 4),
                "average_confidence": 0.89 # Default baseline confidence index
            },
            "message": "Fetched conflict stats successfully."
        })


class ConflictDetailView(ConflictsBaseView):
    """
    GET: Retrieve details of a specific conflict by UUID conflict_id.
    """
    def get(self, request, conflict_id):
        try:
            conflict = KnowledgeConflict.objects.get(conflict_id=conflict_id)
        except ObjectDoesNotExist:
            return Response({
                "success": False,
                "message": "Conflict record not found."
            }, status=status.HTTP_404_NOT_FOUND)
            
        serializer = ConflictSerializer(conflict)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Conflict details resolved successfully."
        })


class ConflictReviewView(ConflictsBaseView):
    """
    POST: Starts human review cycle or updates analyst decision details.
    """
    def post(self, request, conflict_id):
        service = ReviewService()
        action = request.data.get("action", "start") # "start" | "submit"
        
        if action == "start":
            review = service.start_review(conflict_id, request.user)
            serializer = ReviewSerializer(review)
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Conflict review cycle started."
            })
            
        elif action == "submit":
            review_id = request.data.get("review_id")
            decision = request.data.get("decision")
            review_status = request.data.get("status")
            comments = request.data.get("comments", "")
            
            review = service.submit_decision(
                review_id=review_id,
                decision=decision,
                status=review_status,
                comments=comments,
                user=request.user
            )
            serializer = ReviewSerializer(review)
            return Response({
                "success": True,
                "data": serializer.data,
                "message": "Analyst review decision submitted."
            })
            
        return Response({
            "success": False,
            "message": "Unsupported action type parameter."
        }, status=status.HTTP_400_BAD_REQUEST)


class ConflictResolveView(ConflictsBaseView):
    """
    POST: Executes database records modifications or false positive ignore.
    """
    def post(self, request, conflict_id):
        service = ReviewService()
        review_id = request.data.get("review_id")
        resolution = request.data.get("resolution")
        custom_data = request.data.get("custom_edit_data")
        
        result = service.execute_resolution(
            review_id=review_id,
            resolution_type=resolution,
            user=request.user,
            custom_edit_data=custom_data
        )
        
        return Response({
            "success": True,
            "data": result.to_dict(),
            "message": "Conflict resolved successfully."
        })


class ReviewHistoryView(ConflictsBaseView):
    """
    GET: Returns a list of all conflict audit logs.
    """
    def get(self, request):
        service = ReviewService()
        history = service.review_repo.get_history()
        serializer = AuditHistorySerializer(history, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Fetched review audit history successfully."
        })


class ReviewerActionsView(ConflictsBaseView):
    """
    GET: Returns actions list processed by the current requesting reviewer.
    """
    def get(self, request):
        service = ReviewService()
        actions = service.review_repo.get_reviewer_actions(request.user)
        serializer = ReviewSerializer(actions, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Fetched reviewer actions list successfully."
        })


class PendingReviewsView(ConflictsBaseView):
    """
    GET: Returns all reviews with status PENDING or UNDER_REVIEW.
    """
    def get(self, request):
        service = ReviewService()
        pending = service.review_repo.get_pending_reviews()
        serializer = ReviewSerializer(pending, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Fetched pending reviews list successfully."
        })
