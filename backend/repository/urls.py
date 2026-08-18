from django.urls import path, include
from rest_framework.routers import DefaultRouter
from repository.views import KnowledgeDocumentViewSet, KnowledgeRecordViewSet, EmployeeDirectoryViewSet

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='documents')
router.register(r'records', KnowledgeRecordViewSet, basename='records')
router.register(r'employees', EmployeeDirectoryViewSet, basename='employees')

urlpatterns = [
    path('', include(router.urls)),
]

