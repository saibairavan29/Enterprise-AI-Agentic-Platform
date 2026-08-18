from django.urls import path
from .views import (
    ConflictsListView,
    ConflictsStatisticsView,
    ConflictDetailView,
    ConflictReviewView,
    ConflictResolveView,
    ReviewHistoryView,
    ReviewerActionsView,
    PendingReviewsView
)

urlpatterns = [
    path('', ConflictsListView.as_view(), name='conflicts-list'),
    path('statistics/', ConflictsStatisticsView.as_view(), name='conflicts-stats'),
    path('reviews/history/', ReviewHistoryView.as_view(), name='reviews-history'),
    path('reviews/actions/', ReviewerActionsView.as_view(), name='reviewer-actions'),
    path('reviews/pending/', PendingReviewsView.as_view(), name='pending-reviews'),
    path('<uuid:conflict_id>/', ConflictDetailView.as_view(), name='conflict-detail'),
    path('<uuid:conflict_id>/review/', ConflictReviewView.as_view(), name='conflict-review'),
    path('<uuid:conflict_id>/resolve/', ConflictResolveView.as_view(), name='conflict-resolve'),
]
