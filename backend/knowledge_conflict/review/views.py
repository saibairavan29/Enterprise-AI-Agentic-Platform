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
        from rest_framework.exceptions import APIException
        if isinstance(exc, APIException):
            return super().handle_exception(exc)
        logger.error(f"API view exception raised: {str(exc)}", exc_info=True)
        return Response({
            "success": False,
            "errors": [str(exc)],
            "message": "Operation failed."
        }, status=status.HTTP_400_BAD_REQUEST)


def get_active_conflicts():
    """
    Returns QuerySet of KnowledgeConflicts linking strictly ACTIVE repository documents across different files.
    Prevents deleted, archived, or recycled documents from appearing in active scans.
    """
    from django.db.models import Q, F
    return KnowledgeConflict.objects.filter(
        source_document__repository_status='ACTIVE',
        target_document__repository_status='ACTIVE'
    ).exclude(
        source_document=F('target_document')
    ).filter(
        Q(source_document__folder__isnull=True) | Q(source_document__folder__is_deleted=False)
    ).filter(
        Q(target_document__folder__isnull=True) | Q(target_document__folder__is_deleted=False)
    ).exclude(
        source_document__source_document__status__in=['deleted', 'DELETED']
    ).exclude(
        target_document__source_document__status__in=['deleted', 'DELETED']
    )


class ConflictsListView(ConflictsBaseView):
    """
    GET: List all detected conflicts for active repository documents.
    POST: Triggers E2E conflict detection run dynamically.
    """
    def get(self, request):
        params = getattr(request, 'query_params', request.GET)
        status_filter = params.get("status")
        try:
            max_per_pair = int(params.get("max_per_pair", 5))
        except (ValueError, TypeError):
            max_per_pair = 5

        queryset = get_active_conflicts().order_by('-detected_at')
        if status_filter and status_filter != 'ALL':
            queryset = queryset.filter(status=status_filter)
            
        # Diverse sampling: Cap per pair to max_per_pair (default 5) so no single pair floods out other repository files
        seen_pair_counts = {}
        selected_ids = []
        for cid, s_id, t_id in queryset.values_list('id', 'source_document_id', 'target_document_id'):
            pair_key = tuple(sorted([s_id, t_id]))
            cnt = seen_pair_counts.get(pair_key, 0)
            if cnt < max_per_pair:
                seen_pair_counts[pair_key] = cnt + 1
                selected_ids.append(cid)

        diverse_queryset = KnowledgeConflict.objects.filter(id__in=selected_ids).order_by('-overall_similarity', '-detected_at')
        serializer = ConflictSerializer(diverse_queryset, many=True)
        return Response({
            "success": True,
            "data": serializer.data,
            "message": "Fetched conflicts list successfully."
        })

    def post(self, request):
        # Trigger E2E conflict detection orchestrator
        ReviewValidator.validate_reviewer_permissions(request.user)
        
        # 1. Generate comparison candidates from current active repository state
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
    GET: Compiles summary statistical metrics for the active repository dashboard.
    """
    def get(self, request):
        conflicts = get_active_conflicts()
        total_count = conflicts.count()
        pending = conflicts.filter(status__in=['NEW', 'PROCESSING', 'REVIEW_PENDING']).count()
        critical = conflicts.filter(severity='CRITICAL').count()
        verified = conflicts.filter(status='VERIFIED').count()
        
        # Calculate average similarity score across active conflicts
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
                "average_confidence": 0.89
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
