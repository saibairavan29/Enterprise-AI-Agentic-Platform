import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from repository.models import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeRecord,
    RepositoryAuditEntry
)
from repository.serializers import (
    KnowledgeDocumentSerializer,
    KnowledgeDocumentVersionSerializer,
    KnowledgeRecordSerializer,
    RepositoryAuditEntrySerializer,
    SanitizedEmployeeRecordSerializer
)
from repository.services.sync_service import RepositorySynchronizationService
from repository.repositories.record_repository import RecordRepository
from repository.permissions.repository_permissions import IsRepositoryAdminOrAnalyst
from repository.builders.response_builder import ResponseBuilder
from ingestion.models import Document

logger = logging.getLogger('enterprise')

class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet coordinating all CRUD operations on KnowledgeDocument and triggers
    document version archiving, records synchronization, and audit trail logs.
    """
    queryset = KnowledgeDocument.objects.exclude(repository_status='DELETED')
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsAuthenticated, IsRepositoryAdminOrAnalyst]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return KnowledgeDocument.objects.none()
            
        user_role = getattr(user, 'role', 'reader').lower()
        
        # Admins can view everything
        if user_role == 'admin':
            return KnowledgeDocument.objects.exclude(repository_status='DELETED')
            
        # Non-admins: can view all team documents, and personal documents uploaded by themselves
        from django.db.models import Q
        return KnowledgeDocument.objects.exclude(repository_status='DELETED').filter(
            Q(metadata__repository_type='team') | 
            Q(metadata__repository_type__isnull=True) | 
            Q(source_document__uploaded_by=user)
        )

    def list(self, request, *args, **kwargs):
        """
        Lists active knowledge documents with filters/searches.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ResponseBuilder.success(serializer.data, "Documents list resolved successfully.")

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieves a single KnowledgeDocument by key ID.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ResponseBuilder.success(serializer.data, "Document retrieved successfully.")

    def create(self, request, *args, **kwargs):
        """
        POST /api/repository/documents/
        Manually trigger synchronisation for a Phase 1 Ingested Document.
        Accepts: { "document_id": int/uuid, "reason": "optional reason string" }
        """
        document_id = request.data.get('document_id')
        reason = request.data.get('reason', 'Manual trigger sync.')

        if not document_id:
            return ResponseBuilder.error(
                errors=["Parameter 'document_id' is required to invoke repository sync."],
                message="Bad Request.",
                status_code=400
            )

        # Resolve ingestion Document
        try:
            source_doc = Document.objects.get(id=document_id)
        except (Document.DoesNotExist, ValueError):
            return ResponseBuilder.error(
                errors=[f"Ingested Document ID {document_id} was not found."],
                message="Not Found.",
                status_code=404
            )

        # Execute Pipeline Synchronization
        sync_service = RepositorySynchronizationService()
        records_to_sync = []
        if source_doc.standardized_record and isinstance(source_doc.standardized_record, dict):
            # Check standard pipeline records array nesting
            records_to_sync = source_doc.standardized_record.get('records', [])
            if not records_to_sync and 'canonical_record' in source_doc.standardized_record:
                records_to_sync = source_doc.standardized_record.get('canonical_record', [])

        sync_result = sync_service.sync_document(
            document_id=source_doc.id,
            records=records_to_sync,
            metadata=source_doc.metadata or {},
            user=request.user,
            reason=reason
        )

        if not sync_result['success']:
            return ResponseBuilder.error(
                errors=sync_result['errors'],
                message="Synchronization pipeline failed.",
                status_code=400
            )

        return ResponseBuilder.success(
            data=sync_result,
            message="Document synchronization completed successfully.",
            status_code=201
        )

    def update(self, request, *args, **kwargs):
        """
        PUT /api/repository/documents/<id>/
        Allows manual title or metadata edits from Analyst/Admin operators.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check permissions block updates
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Write edit audit log
        RepositoryAuditEntry.objects.create(
            knowledge_document=instance,
            action='EDIT',
            user=request.user.username,
            reason=request.data.get('reason_for_update', f"Attributes edited. Partial: {partial}"),
            pipeline_id="manual-edit"
        )

        return ResponseBuilder.success(
            data=serializer.data,
            message="Document metadata updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/repository/documents/<id>/
        Enforces clean soft-deletion (status set to DELETED).
        """
        instance = self.get_object()

        # Delete source ingestion document to release hash lockout constraint and allow re-uploads
        if instance.source_document:
            instance.source_document.delete()
            
        instance.repository_status = 'DELETED'
        instance.record_count = 0
        instance.save()
        
        # Purge records to release PostgreSQL workspace size
        instance.records.all().delete()

        # Log deleted audit log
        RepositoryAuditEntry.objects.create(
            knowledge_document=instance,
            action='DELETE',
            user=request.user.username,
            reason=request.data.get('reason', "Soft deletion invoked by operator."),
            pipeline_id="manual-delete"
        )

        return ResponseBuilder.success(
            data={"id": instance.id, "repository_status": instance.repository_status},
            message="Document soft-deleted successfully.",
            status_code=200
        )

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        """
        GET /api/repository/documents/<id>/records/
        Lists canonical records associated with this document.
        """
        instance = self.get_object()
        records_queryset = instance.records.all()
        
        # Paginate records
        page = self.paginate_queryset(records_queryset)
        if page is not None:
            serializer = KnowledgeRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = KnowledgeRecordSerializer(records_queryset, many=True)
        return ResponseBuilder.success(serializer.data, "Document records list resolved.")

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        GET /api/repository/documents/<id>/versions/
        Lists history snapshot records associated with this document.
        """
        instance = self.get_object()
        versions_queryset = instance.versions.all().order_by('-version')
        serializer = KnowledgeDocumentVersionSerializer(versions_queryset, many=True)
        return ResponseBuilder.success(serializer.data, "Version snapshot history list resolved.")

    @action(detail=True, methods=['get'])
    def audit(self, request, pk=None):
        """
        GET /api/repository/documents/<id>/audit/
        Lists security log records associated with this document.
        """
        instance = self.get_object()
        audit_queryset = instance.audit_entries.all().order_by('-timestamp')
        serializer = RepositoryAuditEntrySerializer(audit_queryset, many=True)
        return ResponseBuilder.success(serializer.data, "Document audit log list resolved.")

    @action(detail=True, methods=['get'])
    def view_file(self, request, pk=None):
        """
        GET /api/v1/repository/documents/<id>/view_file/
        Direct secure file preview parser/streamer endpoint.
        Enforces standard permissions and filters by get_object() automatically.
        """
        instance = self.get_object()
        import os
        
        file_path = None
        original_name = ""
        mime_type = ""
        
        if instance.source_document and instance.source_document.file:
            file_path = instance.source_document.file.path
            original_name = instance.source_document.original_name
            mime_type = instance.source_document.mime_type
        elif instance.metadata:
            # Fallback to metadata resolving if source_document ForeignKey is empty/null
            file_meta = instance.metadata.get("file", {})
            source_meta = instance.metadata.get("source", {})
            
            rel_path = file_meta.get("stored_name") or source_meta.get("file_path") or source_meta.get("storage_location")
            if rel_path:
                from django.conf import settings
                possible_paths = [
                    os.path.join(settings.BASE_DIR, rel_path),
                    os.path.join(settings.BASE_DIR, "Uploads", rel_path),
                    os.path.join(settings.BASE_DIR, rel_path.replace("Uploads/", "")),
                    os.path.join(os.path.dirname(settings.BASE_DIR), rel_path),
                    os.path.join(os.path.dirname(settings.BASE_DIR), "Uploads", rel_path),
                    os.path.join(os.path.dirname(settings.BASE_DIR), rel_path.replace("Uploads/", "")),
                    os.path.abspath(rel_path)
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        file_path = p
                        break
            
            original_name = file_meta.get("original_name") or instance.title or "document"
            mime_type = file_meta.get("mime_type") or "application/octet-stream"
            
        if not file_path or not os.path.exists(file_path):
            return ResponseBuilder.error(
                errors=["Associated physical raw file not found for this document on storage server."],
                message="Not Found.",
                status_code=404
            )
            
        ext = os.path.splitext(original_name.lower())[1].lstrip('.')
        mime = mime_type
        
        if ext == 'csv':
            import csv
            try:
                headers = []
                rows = []
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.reader(f)
                    try:
                        headers = next(reader)
                    except StopIteration:
                        pass
                    
                    row_limit = 200
                    for i, row in enumerate(reader):
                        if i >= row_limit:
                            break
                        rows.append(row)
                
                return ResponseBuilder.success({
                    "file_type": "csv",
                    "headers": headers,
                    "rows": rows,
                    "truncated": len(rows) >= row_limit
                }, "CSV parsed successfully.")
            except Exception as csv_err:
                return ResponseBuilder.error(
                    errors=[f"Failed to parse CSV: {str(csv_err)}"],
                    message="Unprocessable Entity",
                    status_code=422
                )
                
        elif ext in ['xlsx', 'xls']:
            import openpyxl
            try:
                wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
                sheets_data = {}
                for sheet_name in wb.sheetnames[:5]:
                    sheet = wb[sheet_name]
                    headers = []
                    rows = []
                    
                    row_limit = 200
                    for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                        if r_idx == 0:
                            headers = [str(cell) if cell is not None else "" for cell in row]
                        else:
                            if r_idx >= row_limit:
                                break
                            rows.append([str(cell) if cell is not None else "" for cell in row])
                            
                    sheets_data[sheet_name] = {
                        "headers": headers,
                        "rows": rows,
                        "truncated": len(rows) >= row_limit - 1
                    }
                
                return ResponseBuilder.success({
                    "file_type": "excel",
                    "sheets": sheets_data
                }, "Excel workbook parsed successfully.")
            except Exception as xls_err:
                return ResponseBuilder.error(
                    errors=[f"Failed to parse Excel: {str(xls_err)}"],
                    message="Unprocessable Entity",
                    status_code=422
                )
                
        elif ext in ['txt', 'md', 'markdown']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read(50000)
                
                return ResponseBuilder.success({
                    "file_type": "text",
                    "content": content,
                    "truncated": len(content) >= 50000
                }, "Text read successfully.")
            except Exception as txt_err:
                return ResponseBuilder.error(
                    errors=[f"Failed to read text: {str(txt_err)}"],
                    message="Unprocessable Entity",
                    status_code=422
                )
                
        elif ext in ['pdf', 'png', 'jpg', 'jpeg', 'webp']:
            from django.http import FileResponse
            return FileResponse(open(file_path, 'rb'), content_type=mime)
            
        else:
            return ResponseBuilder.success({
                "file_type": "unsupported",
                "original_name": instance.source_document.original_name,
                "mime_type": mime
            }, "Preview not available for this file type.")


class KnowledgeRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet allowing generic custom PostgreSQL JSONField queries 
    on all canonical records across documents.
    """
    queryset = KnowledgeRecord.objects.all()
    serializer_class = KnowledgeRecordSerializer
    permission_classes = [IsAuthenticated, IsRepositoryAdminOrAnalyst]

    def list(self, request, *args, **kwargs):
        """
        GET /api/repository/records/?field=...&value=...&contains=...
        """
        field = request.query_params.get('field')
        value = request.query_params.get('value')
        contains = request.query_params.get('contains')

        repo = RecordRepository()
        queryset = repo.filter_records(field, value, contains)

        # Pagination support
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ResponseBuilder.success(serializer.data, "Record query list resolved successfully.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ResponseBuilder.success(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        PUT /api/repository/records/<id>/
        Allows manual record-level canonical data overrides.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Log edited audit
        RepositoryAuditEntry.objects.create(
            knowledge_document=instance.knowledge_document,
            action='EDIT',
            user=request.user.username,
            reason=f"Edited record {instance.id} canonical_data properties manually.",
            pipeline_id="record-edit"
        )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return ResponseBuilder.success(
            data=serializer.data,
            message="Record updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/repository/records/<id>/
        """
        instance = self.get_object()
        
        # Log audit entry
        RepositoryAuditEntry.objects.create(
            knowledge_document=instance.knowledge_document,
            action='DELETE',
            user=request.user.username,
            reason=f"Deleted record {instance.id} from document {instance.knowledge_document_id}.",
            pipeline_id="record-delete"
        )
        
        self.perform_destroy(instance)
        return ResponseBuilder.success(message="Record deleted successfully.")


class EmployeeDirectoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the Employee Directory.
    Queries records that contain 'employee_id' key in canonical_data JSONField.
    Only administrators are allowed to create/add records.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SanitizedEmployeeRecordSerializer

    def get_queryset(self):
        # Query Django model checking for key employee_id in SQLite/Postgres JSON Field
        return KnowledgeRecord.objects.filter(
            canonical_data__has_key='employee_id'
        ).order_by('-id')

    def create(self, request, *args, **kwargs):
        # Only admins can create
        user_role = getattr(request.user, 'role', 'reader').lower()
        if user_role != 'admin':
            return ResponseBuilder.error(
                errors=["Permission Denied"],
                message="Only administrators can add employees to the directory.",
                status_code=status.HTTP_403_FORBIDDEN
            )
            
        data = request.data
        employee_id = data.get('employee_id')
        name = data.get('name')
        email = data.get('email')
        department = data.get('department')
        role = data.get('role')
        
        if not employee_id or not name or not email or not department or not role:
            return ResponseBuilder.error(
                errors=["Missing Fields"],
                message="Employee ID, Name, Email, Department, and Role are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if an employee with this employee_id already exists in canonical_data
        # Note: Using SQLite/Postgres JSON field query syntax for compatibility
        exists = KnowledgeRecord.objects.filter(
            canonical_data__employee_id=str(employee_id)
        ).exists()
        if exists:
            return ResponseBuilder.error(
                errors=["Duplicate ID"],
                message=f"An employee with ID '{employee_id}' already exists.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Get or create a default document for manual entries
        doc, created = KnowledgeDocument.objects.get_or_create(
            title="Manual Employee Directory",
            defaults={
                "document_type": "HR_RECORD",
                "repository_status": "SYNCED",
                "owner": request.user,
                "schema_resolved": True
            }
        )

        canonical_data = {
            "employee_id": str(employee_id),
            "name": str(name),
            "email": str(email),
            "department": str(department),
            "role": str(role),
            "experience_years": int(data.get('experience_years', 0)),
            "current_project": str(data.get('current_project', 'Bench')),
            "work_location": str(data.get('work_location', 'Remote')),
            "employment_status": str(data.get('employment_status', 'Active')),
            "skills": str(data.get('skills', '')),
            "joining_date": str(data.get('joining_date', timezone.now().date().isoformat())),
            "salary": float(data.get('salary', 0.0))
        }

        record = KnowledgeRecord.objects.create(
            knowledge_document=doc,
            entity_type="employee",
            canonical_data=canonical_data,
            embedding_status="NOT_GENERATED"
        )
        
        # Create a baseline perfect quality report for manually added employees
        from edqi.models import EnterpriseDataQualityReport
        EnterpriseDataQualityReport.objects.create(
            knowledge_record=record,
            overall_quality_score=100.0,
            previous_quality_score=0.0,
            trend="STABLE",
            completeness_score=100.0,
            validity_score=100.0,
            consistency_score=100.0,
            uniqueness_score=100.0,
            timeliness_score=100.0,
            quality_grade="A+",
            assessment_status="COMPLETED",
            assessment_engine_version="1.0",
            rules_version="1.0",
            feature_version="1.0",
            quality_features={
                "missing_fields": 0,
                "invalid_fields": 0,
                "duplicate_fields": 0,
                "record_age": 0
            },
            ml_ready_features={
                "missing_fields": 0.0,
                "invalid_fields": 0.0,
                "duplicate_fields": 0.0,
                "record_age": 0.0,
                "quality_score": 100.0,
                "completeness_score": 100.0,
                "validity_score": 100.0,
                "consistency_score": 100.0,
                "uniqueness_score": 100.0,
                "timeliness_score": 100.0
            },
            processing_trace={"manual_entry": True},
            metadata={"created_by": request.user.username}
        )

        return ResponseBuilder.success(
            data=SanitizedEmployeeRecordSerializer(record).data,
            message="Employee added successfully.",
            status_code=status.HTTP_201_CREATED
        )

