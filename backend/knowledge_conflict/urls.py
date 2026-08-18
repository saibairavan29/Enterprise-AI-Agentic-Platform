from django.urls import path, include

urlpatterns = [
    # Include review APIs as root endpoints for knowledge_conflict
    path('', include('knowledge_conflict.review.urls')),
]
