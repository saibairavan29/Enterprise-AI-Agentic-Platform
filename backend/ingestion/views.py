import logging
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import DocumentUploadSerializer
from .services.upload_service import DocumentUploadService

logger = logging.getLogger('enterprise')

class DocumentUploadView(APIView):
    """
    API endpoint accepting file uploads (multipart/form-data).
    Validates formatting, content types, checks for duplicates,
    and returns a formatted success or error response.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        logger.info(f"File upload attempt received from user: {request.user.username}")
        
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        
        try:
            # Instantiate the upload service with retry resilience for transient SQLite locks
            upload_service = DocumentUploadService()
            doc = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    doc = upload_service.execute(uploaded_file, request.user)
                    break
                except Exception as exc:
                    if 'database is locked' in str(exc).lower() and attempt < max_retries - 1:
                        import time
                        from django import db
                        db.connections.close_all()
                        time.sleep(0.15)
                        uploaded_file.seek(0)
                    else:
                        raise exc
            
            # Save repository type visibility scope and folder path in metadata
            repository_type = serializer.validated_data.get('repository_type', 'team')
            folder_id = serializer.validated_data.get('folder_id', '')
            relative_path = serializer.validated_data.get('relative_path', '')
            target_logical_path = serializer.validated_data.get('target_logical_path', '')
            
            doc.metadata = {
                "repository_type": repository_type,
                "folder_id": folder_id,
                "relative_path": relative_path,
                "target_logical_path": target_logical_path
            }
            doc.processing_status = 'PROCESSING'
            doc.save()
            
            # Dispatch background ingestion pipeline (decoupled HTTP execution)
            from .orchestration.services.orchestration_service import IngestionOrchestrationService
            orchestrator = IngestionOrchestrationService()
            orchestrator.process_document_async(doc.id, request.user)
            
            # Format response returning immediately after upload registration (status code 201)
            return Response({
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "File uploaded successfully. Ingestion processing started in background.",
                "data": {
                    "document_id": doc.id,
                    "file_name": doc.original_name,
                    "file_size": doc.file_size,
                    "processing_status": "PROCESSING"
                },
                "errors": [],
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except DjangoValidationError as e:
            msg = e.message if hasattr(e, 'message') else (', '.join(e.messages) if hasattr(e, 'messages') else str(e))
            logger.warning(f"File upload validation failed: {msg}")
            return Response({
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": msg,
                "data": {},
                "errors": [msg],
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error during document upload view handler: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": str(e),
                "data": {},
                "errors": [str(e)],
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)


class DocumentStatusView(APIView):
    """
    API endpoint returning real-time processing status, real stage states, and ProcessingHistory records.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, doc_id, *args, **kwargs):
        from .models import Document
        try:
            doc = Document.objects.get(id=doc_id)
            histories = doc.processing_histories.all().order_by('id')
            
            all_stages = ['Validation', 'Parser', 'OCR', 'Metadata', 'SchemaMapping', 'Standardization', 'Persistence']
            stage_history_map = {h.stage_name: h for h in histories}
            
            stage_execution = {}
            current_stage = None
            last_failed_stage = None
            
            for stage_name in all_stages:
                if stage_name in stage_history_map:
                    h = stage_history_map[stage_name]
                    stage_execution[stage_name] = {
                        "status": h.stage_status,
                        "execution_time": h.execution_duration,
                        "start_time": h.start_time.isoformat() if h.start_time else None,
                        "end_time": h.end_time.isoformat() if h.end_time else None
                    }
                    if h.stage_status == 'EXECUTING':
                        current_stage = stage_name
                    elif h.stage_status == 'FAILED':
                        last_failed_stage = stage_name
                else:
                    stage_execution[stage_name] = {
                        "status": "PENDING",
                        "execution_time": 0.0,
                        "start_time": None,
                        "end_time": None
                    }

            elapsed_time = round((timezone.now() - doc.created_at).total_seconds(), 3)
            
            # Lightweight standardized preview if completed
            std_record_preview = None
            if doc.processing_status == 'COMPLETED' and doc.standardized_record:
                std_rec = doc.standardized_record
                if isinstance(std_rec, dict):
                    raw_recs = std_rec.get("standardized_record", []) or std_rec.get("records", [])
                    if isinstance(raw_recs, list):
                        preview_list = raw_recs[:10]
                        std_record_preview = {
                            "records_preview": preview_list,
                            "total_records": len(raw_recs),
                            "preview_truncated": len(raw_recs) > 10
                        }
                    else:
                        std_record_preview = std_rec

            return Response({
                "success": True,
                "document_id": doc.id,
                "file_name": doc.original_name,
                "file_size": doc.file_size,
                "processing_status": doc.processing_status,
                "current_stage": current_stage,
                "last_failed_stage": last_failed_stage,
                "elapsed_time": elapsed_time,
                "stage_execution": stage_execution,
                "standardized_preview": std_record_preview,
                "metadata": doc.metadata or {}
            })
        except Document.DoesNotExist:
            return Response({
                "success": False,
                "message": f"Document ID {doc_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

