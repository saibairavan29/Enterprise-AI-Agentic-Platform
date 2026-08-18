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
            # Instantiate the upload service
            upload_service = DocumentUploadService()
            doc = upload_service.execute(uploaded_file, request.user)
            
            # Save repository type visibility scope in metadata
            repository_type = serializer.validated_data.get('repository_type', 'team')
            doc.metadata = {"repository_type": repository_type}
            doc.save()
            
            # Trigger pipeline orchestration
            from .orchestration.services.orchestration_service import IngestionOrchestrationService
            orchestrator = IngestionOrchestrationService()
            orchestrator_res = orchestrator.process_document(doc.id, request.user)
            
            # Fetch updated document state
            doc.refresh_from_db()
            
            if not orchestrator_res.get("success", False):
                doc.delete()  # Clean up failed document record to allow re-upload attempts
                return Response({
                    "success": False,
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Document uploaded but pipeline execution failed.",
                    "data": {
                        "document_id": doc.id,
                        "file_name": doc.original_name,
                        "processing_status": doc.processing_status,
                        "pipeline_result": orchestrator_res
                    },
                    "errors": orchestrator_res.get("errors", []),
                    "timestamp": timezone.now().isoformat()
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
            # Format successful response matching refined schema (status code 201)
            return Response({
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "Document uploaded and processed successfully.",
                "data": {
                    "document_id": doc.id,
                    "file_name": doc.original_name,
                    "processing_status": doc.processing_status,
                    "pipeline_result": orchestrator_res
                },
                "errors": [],
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_201_CREATED)
            
        except DjangoValidationError as e:
            logger.warning(f"File upload validation failed: {str(e)}")
            return Response({
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": e.message if hasattr(e, 'message') else str(e),
                "data": {},
                "errors": e.message_dict if hasattr(e, 'message_dict') else [str(e)],
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Critical error during document upload view handler: {str(e)}", exc_info=True)
            raise e
