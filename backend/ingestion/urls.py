from django.urls import path
from .views import DocumentUploadView, DocumentStatusView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document_upload'),
    path('status/<int:doc_id>/', DocumentStatusView.as_view(), name='document_status'),
]
