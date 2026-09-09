from django.urls import path, include
from rest_framework.routers import DefaultRouter
from repository.views import (
    KnowledgeDocumentViewSet, 
    KnowledgeRecordViewSet, 
    EmployeeDirectoryViewSet,
    RepositoryFolderViewSet,
    RepositoryExplorerView,
    RecycleBinView
)

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='documents')
router.register(r'records', KnowledgeRecordViewSet, basename='records')
router.register(r'employees', EmployeeDirectoryViewSet, basename='employees')
router.register(r'folders', RepositoryFolderViewSet, basename='folders')

urlpatterns = [
    path('explorer/', RepositoryExplorerView.as_view(), name='repository-explorer'),
    path('recycle-bin/', RecycleBinView.as_view(), name='repository-recycle-bin'),
    path('', include(router.urls)),
]

