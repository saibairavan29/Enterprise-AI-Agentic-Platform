from django.urls import path
from .views import (
    ChatQueryEndpoint,
    ChatHistoryEndpoint,
    SessionListEndpoint,
    SessionDetailEndpoint,
    ReindexDatasetEndpoint
)

urlpatterns = [
    path('chat/', ChatQueryEndpoint.as_view(), name='assistant_chat'),
    path('sessions/', SessionListEndpoint.as_view(), name='assistant_sessions_list'),
    path('sessions/<uuid:session_id>/', SessionDetailEndpoint.as_view(), name='assistant_session_detail'),
    path('history/', ChatHistoryEndpoint.as_view(), name='assistant_history'),
    path('reindex/', ReindexDatasetEndpoint.as_view(), name='assistant_reindex'),
]

