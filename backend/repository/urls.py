from django.urls import path, include
from rest_framework.routers import DefaultRouter
from repository.views import (
    KnowledgeDocumentViewSet, 
    KnowledgeRecordViewSet, 
    EmployeeDirectoryViewSet,
    RepositoryFolderViewSet,
    RepositoryExplorerView,
    RecycleBinView,
    DashboardSummaryView,
    RepositoryLatestStatusView
)

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='documents')
router.register(r'records', KnowledgeRecordViewSet, basename='records')
router.register(r'employees', EmployeeDirectoryViewSet, basename='employees')
router.register(r'folders', RepositoryFolderViewSet, basename='folders')

urlpatterns = [
    path('latest-status/', RepositoryLatestStatusView.as_view(), name='repository-latest-status'),
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='repository-dashboard-summary'),
    path('explorer/', RepositoryExplorerView.as_view(), name='repository-explorer'),
    path('recycle-bin/', RecycleBinView.as_view(), name='repository-recycle-bin'),
    path('', include(router.urls)),
]

