from django.urls import path
from edqi.explainability.views import (
    GenerateExplanationView,
    ExplanationHistoryView,
    ExplanationDetailView,
    RecommendationHistoryView,
    RecommendationPredictionDetailView,
    ExplainabilityStatisticsView,
    ExplainabilityModelsView,
    ExplainabilityCacheStatsView
)

urlpatterns = [
    # Core XAI Endpoints
    path('edqi/explain/', GenerateExplanationView.as_view(), name='explain-generate'),
    path('edqi/explanations/', ExplanationHistoryView.as_view(), name='explain-history'),
    path('edqi/explanations/<uuid:pk>/', ExplanationDetailView.as_view(), name='explain-detail'),
    
    # Recommendations Endpoints
    path('edqi/recommendations/', RecommendationHistoryView.as_view(), name='recommendation-history'),
    path('edqi/recommendations/<uuid:prediction_id>/', RecommendationPredictionDetailView.as_view(), name='recommendation-prediction'),
    
    # Statistics and Cache APIs
    path('edqi/explainability/statistics/', ExplainabilityStatisticsView.as_view(), name='explain-statistics'),
    path('explainability/models/', ExplainabilityModelsView.as_view(), name='explain-models'),
    path('explainability/cache/statistics/', ExplainabilityCacheStatsView.as_view(), name='explain-cache-stats'),
]
