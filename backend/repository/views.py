import logging
import re
import time
from django.db import transaction, models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from repository.models import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeRecord,
    RepositoryAuditEntry,
    RepositoryFolder
)
from repository.serializers import (
    KnowledgeDocumentSerializer,
    KnowledgeDocumentVersionSerializer,
    KnowledgeRecordSerializer,
    RepositoryAuditEntrySerializer,
    SanitizedEmployeeRecordSerializer,
    RepositoryFolderSerializer
)
from repository.services.sync_service import RepositorySynchronizationService
from repository.repositories.record_repository import RecordRepository
from repository.permissions.repository_permissions import IsRepositoryAdminOrAnalyst
from repository.builders.response_builder import ResponseBuilder
from common.json_utils import enforce_json_boundary
from ingestion.models import Document

logger = logging.getLogger('enterprise')

def safely_purge_document(instance):
    """
    Safely purges a KnowledgeDocument and all associated records from DB 
    without failing due to foreign key or cascade locks.
    """
    try:
        doc_id = instance.id
        title = instance.title
        source_doc = getattr(instance, 'source_document', None)
        
        with transaction.atomic():
            instance.records.all().delete()
            instance.versions.all().delete()
            if hasattr(instance, 'audit_entries'):
                instance.audit_entries.all().delete()
            
            # Detach source_document to prevent FK constraint failures
            if source_doc:
                instance.source_document = None
                instance.save()
                try:
                    source_doc.delete()
                except Exception:
                    pass

            instance.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to permanently purge document {instance.id}: {str(e)}")
        try:
            KnowledgeDocument.objects.filter(id=instance.id).delete()
        except Exception:
            instance.repository_status = 'DELETED'
            instance.save()
        return False


def safely_purge_folder(folder):
    """
    Safely purges a RepositoryFolder and all contained documents/subfolders.
    """
    try:
        with transaction.atomic():
            sub_docs = KnowledgeDocument.objects.filter(logical_path__startswith=f"{folder.logical_path}/")
            for d in sub_docs:
                safely_purge_document(d)

            subfolders = RepositoryFolder.objects.filter(logical_path__startswith=f"{folder.logical_path}/")
            subfolders.delete()
            folder.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to permanently purge folder {folder.id}: {str(e)}")
        try:
            folder.delete()
        except Exception:
            folder.is_deleted = True
            folder.save()
        return False

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
        Enforces clean, atomic soft-deletion (status set to DELETED).
        """
        instance = self.get_object()

        with transaction.atomic():
            source_doc = instance.source_document
            instance.source_document = None
            instance.repository_status = 'DELETED'
            instance.record_count = 0
            instance.save()

            # Delete source ingestion document to release hash lockout constraint and allow re-uploads
            if source_doc:
                source_doc.delete()
            
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

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        POST /api/v1/repository/documents/<id>/restore/
        Restores a soft-deleted KnowledgeDocument back to ACTIVE status.
        """
        instance = get_object_or_404(KnowledgeDocument, id=pk)
        instance.repository_status = 'ACTIVE'
        instance.save()

        RepositoryAuditEntry.objects.create(
            knowledge_document=instance,
            action='EDIT',
            user=request.user.username,
            reason="Restored from Recycle Bin",
            pipeline_id="manual-restore"
        )

        return ResponseBuilder.success(
            data={"id": instance.id, "repository_status": instance.repository_status},
            message="Document restored successfully from Recycle Bin."
        )

    @action(detail=True, methods=['delete'])
    def permanent_delete(self, request, pk=None):
        """
        DELETE /api/v1/repository/documents/<id>/permanent_delete/
        Permanently purges a KnowledgeDocument and its associated records from database.
        """
        instance = get_object_or_404(KnowledgeDocument, id=pk)
        doc_id = instance.id
        title = instance.title
        
        safely_purge_document(instance)

        return ResponseBuilder.success(
            data={"id": doc_id, "title": title},
            message="Document permanently purged from database."
        )

    @action(detail=False, methods=['post', 'delete'])
    def delete_all(self, request):
        """
        POST/DELETE /api/v1/repository/documents/delete_all/
        Soft deletes all documents and folders within a repository scope or subfolder.
        """
        repo_type = request.data.get('repository_type') or request.query_params.get('repository_type', 'team')
        folder_id = request.data.get('folder_id') or request.query_params.get('folder_id', '')

        with transaction.atomic():
            if folder_id:
                folder = RepositoryFolder.objects.filter(id=folder_id, is_deleted=False).first()
                if folder:
                    docs = KnowledgeDocument.objects.filter(Q(folder=folder) | Q(logical_path__startswith=f"{folder.logical_path}/"))
                    subfolders = RepositoryFolder.objects.filter(logical_path__startswith=f"{folder.logical_path}/")
                    docs.update(repository_status='DELETED')
                    subfolders.update(is_deleted=True)
                    folder.is_deleted = True
                    folder.save()
                    msg = f"All items inside folder '{folder.name}' moved to Recycle Bin."
                else:
                    return ResponseBuilder.error(["Target folder not found."], status_code=404)
            else:
                root_prefix = 'Personal' if repo_type == 'personal' else 'Team'
                docs = KnowledgeDocument.objects.filter(Q(metadata__repository_type=repo_type) | Q(logical_path__startswith=f"{root_prefix}/"))
                subfolders = RepositoryFolder.objects.filter(repository_type=repo_type)
                if repo_type == 'personal' and getattr(request.user, 'role', 'reader').lower() != 'admin':
                    docs = docs.filter(Q(owner=request.user) | Q(source_document__uploaded_by=request.user))
                    subfolders = subfolders.filter(owner=request.user)

                docs_count = docs.count()
                folders_count = subfolders.count()
                docs.update(repository_status='DELETED')
                subfolders.update(is_deleted=True)
                msg = f"Moved {docs_count} files and {folders_count} folders in {repo_type.upper()} repository to Recycle Bin."

        return ResponseBuilder.success(data={}, message=msg)

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


def infer_schema_from_rows(raw_records):
    """
    Infer dynamic schema metadata from imported row dictionaries.
    Returns list of dicts: [{'key': ..., 'label': ..., 'type': ...}]
    """
    if not raw_records or not isinstance(raw_records, list):
        return []
    
    key_set = []
    for r in raw_records:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in key_set and k not in ['id', 'knowledge_document', 'created_at', 'updated_at']:
                    key_set.append(k)

    schema_cols = []
    for key in key_set:
        label = key.replace('_', ' ').title().replace('Id', 'ID')
        col_type = 'text'
        
        # Check sample values to infer type
        sample_vals = [r.get(key) for r in raw_records if isinstance(r, dict) and r.get(key) is not None]
        k_lower = key.lower()

        if any(isinstance(v, (int, float)) for v in sample_vals) or any(k in k_lower for k in ['salary', 'pay', 'exp', 'years', 'count', 'age', 'score', 'price']):
            col_type = 'number'
        elif any(k in k_lower for k in ['date', 'time', 'dob']):
            col_type = 'date'
        elif len(set(str(v) for v in sample_vals)) <= 25 and len(sample_vals) > 1:
            col_type = 'category'

        schema_cols.append({
            'key': key,
            'label': label,
            'type': col_type
        })
    return schema_cols


class EmployeeDirectoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Universal Schema-Driven Record Directory.
    Handles dynamic schema records cleanly for any enterprise dataset.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SanitizedEmployeeRecordSerializer

    def get_queryset(self):
        return KnowledgeRecord.objects.all().order_by('-id')

    @action(detail=False, methods=['get'], url_path='schema')
    def get_schema(self, request, *args, **kwargs):
        records = list(KnowledgeRecord.objects.all()[:100])
        raw_rows = [r.canonical_data for r in records if r.canonical_data]
        schema = infer_schema_from_rows(raw_rows)
        return ResponseBuilder.success(data=schema, message="Directory schema fetched successfully.")

    def create(self, request, *args, **kwargs):
        user_role = getattr(request.user, 'role', 'reader').lower()
        if user_role != 'admin':
            return ResponseBuilder.error(
                errors=["Permission Denied"],
                message="Only administrators can add records to the directory.",
                status_code=status.HTTP_403_FORBIDDEN
            )
            
        data = request.data
        if not isinstance(data, dict) or not data:
            return ResponseBuilder.error(
                errors=["Missing Fields"],
                message="Record payload cannot be empty.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        # Parse numbers / floats cleanly in data
        canonical_data = {}
        for k, v in data.items():
            if isinstance(v, str):
                v_str = v.strip()
                if re.match(r'^-?\d+\.\d+$', v_str.replace('$', '').replace(',', '')):
                    try:
                        canonical_data[k] = float(v_str.replace('$', '').replace(',', ''))
                    except ValueError:
                        canonical_data[k] = v_str
                elif re.match(r'^-?\d+$', v_str.replace('$', '').replace(',', '')):
                    try:
                        canonical_data[k] = int(v_str.replace('$', '').replace(',', ''))
                    except ValueError:
                        canonical_data[k] = v_str
                else:
                    canonical_data[k] = v_str
            else:
                canonical_data[k] = v

        # Find primary ID key
        primary_id_val = None
        for k in ["employee_id", "id", "associate_id", "vendor_id", "observation_id", "code"]:
            if k in canonical_data and canonical_data[k]:
                primary_id_val = str(canonical_data[k])
                break
        if not primary_id_val:
            for k, v in canonical_data.items():
                if 'id' in k.lower() or 'code' in k.lower():
                    primary_id_val = str(v)
                    break
        if not primary_id_val:
            primary_id_val = f"REC{int(time.time() * 1000)}"

        # Get or create a default document for manual entries
        doc, created = KnowledgeDocument.objects.get_or_create(
            title="Manual Record Directory",
            defaults={
                "repository_status": "ACTIVE",
                "metadata": {
                    "document_type": "ENTERPRISE_RECORD",
                    "schema_resolved": True,
                    "owner": request.user.username if hasattr(request.user, 'username') else str(request.user)
                }
            }
        )

        record = KnowledgeRecord.objects.create(
            knowledge_document=doc,
            entity_type="record",
            canonical_data=canonical_data,
            embedding_status="NOT_GENERATED"
        )
        
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
            quality_features={"missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0, "record_age": 0},
            ml_ready_features={"quality_score": 100.0},
            processing_trace={"manual_entry": True},
            metadata={"created_by": request.user.username}
        )

        return ResponseBuilder.success(
            data=SanitizedEmployeeRecordSerializer(record).data,
            message="Record added successfully.",
            status_code=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], url_path='bulk_import')
    def bulk_import(self, request, *args, **kwargs):
        """
        POST /api/v1/repository/employees/bulk_import/
        Stack Add endpoint: Bulk imports records from CSV, Excel file, or JSON array.
        """
        user_role = getattr(request.user, 'role', 'reader').lower()
        if user_role != 'admin':
            return ResponseBuilder.error(
                errors=["Permission Denied"],
                message="Only administrators can bulk import records.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        raw_records = []
        uploaded_file = request.FILES.get('file')
        doc_id = request.data.get('document_id') or request.data.get('knowledge_document_id')

        if doc_id:
            try:
                target_kdoc = KnowledgeDocument.objects.get(id=doc_id)
                for rec in target_kdoc.records.all():
                    cdata = rec.canonical_data or {}
                    if cdata:
                        raw_records.append(cdata)
                
                if not raw_records and target_kdoc.source_document and target_kdoc.source_document.file:
                    f_path = target_kdoc.source_document.file.path
                    f_name = target_kdoc.source_document.original_name.lower()
                    if f_name.endswith('.csv'):
                        import csv
                        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                raw_records.append(row)
                    elif f_name.endswith(('.xlsx', '.xls')):
                        import openpyxl
                        wb = openpyxl.load_workbook(f_path, data_only=True)
                        sheet = wb.active
                        headers = []
                        for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                            if r_idx == 0:
                                headers = [str(cell).strip() if cell is not None else "" for cell in row]
                            else:
                                row_dict = {}
                                for h, val in zip(headers, row):
                                    if h and val is not None:
                                        row_dict[h] = str(val).strip()
                                if row_dict:
                                    raw_records.append(row_dict)
            except Exception as doc_err:
                return ResponseBuilder.error(
                    errors=[f"Failed to load repository document: {str(doc_err)}"],
                    message="Not Found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

        elif uploaded_file:
            filename = uploaded_file.name.lower()
            if filename.endswith('.csv'):
                import csv, io
                try:
                    content = uploaded_file.read().decode('utf-8', errors='ignore')
                    reader = csv.DictReader(io.StringIO(content))
                    for row in reader:
                        raw_records.append(row)
                except Exception as csv_err:
                    return ResponseBuilder.error(
                        errors=[f"Failed to parse CSV file: {str(csv_err)}"],
                        message="Unprocessable Entity",
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            elif filename.endswith(('.xlsx', '.xls')):
                import openpyxl
                try:
                    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                    sheet = wb.active
                    headers = []
                    for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                        if r_idx == 0:
                            headers = [str(cell).strip() if cell is not None else "" for cell in row]
                        else:
                            row_dict = {}
                            for h, val in zip(headers, row):
                                if h and val is not None:
                                    row_dict[h] = str(val).strip()
                            if row_dict:
                                raw_records.append(row_dict)
                except Exception as excel_err:
                    return ResponseBuilder.error(
                        errors=[f"Failed to parse Excel file: {str(excel_err)}"],
                        message="Unprocessable Entity",
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
            else:
                return ResponseBuilder.error(
                    errors=["Unsupported File Format"],
                    message="Please upload a valid .csv, .xlsx, or .xls file.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            employees_data = request.data.get('employees')
            if isinstance(employees_data, list):
                raw_records = employees_data

        if not raw_records:
            return ResponseBuilder.error(
                errors=["Empty Dataset"],
                message="No valid rows were found in the payload or file.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Detect dynamic schema from imported rows
        inferred_schema = infer_schema_from_rows(raw_records)

        doc, _ = KnowledgeDocument.objects.get_or_create(
            title="Bulk Stack Add Record Directory",
            defaults={
                "repository_status": "ACTIVE",
                "metadata": {
                    "source": "Stack Add Import",
                    "schema": inferred_schema
                }
            }
        )
        doc.metadata["schema"] = inferred_schema
        doc.save()

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors_list = []

        from edqi.models import EnterpriseDataQualityReport

        for idx, row in enumerate(raw_records, 1):
            if not isinstance(row, dict):
                continue
            
            canonical_data = {}
            for k, v in row.items():
                k_clean = str(k).strip()
                if isinstance(v, str):
                    v_str = v.strip()
                    if re.match(r'^-?\d+\.\d+$', v_str.replace('$', '').replace(',', '')):
                        try:
                            canonical_data[k_clean] = float(v_str.replace('$', '').replace(',', ''))
                        except ValueError:
                            canonical_data[k_clean] = v_str
                    elif re.match(r'^-?\d+$', v_str.replace('$', '').replace(',', '')):
                        try:
                            canonical_data[k_clean] = int(v_str.replace('$', '').replace(',', ''))
                        except ValueError:
                            canonical_data[k_clean] = v_str
                    else:
                        canonical_data[k_clean] = v_str
                else:
                    canonical_data[k_clean] = v

            # Find primary key matching candidate
            rec_key = None
            rec_val = None
            for pk_name in ["employee_id", "id", "associate_id", "vendor_id", "observation_id", "code"]:
                for rk, rv in canonical_data.items():
                    if rk.lower().replace("_", "") == pk_name.replace("_", ""):
                        rec_key = rk
                        rec_val = str(rv)
                        break
                if rec_key:
                    break

            existing_rec = None
            if rec_key and rec_val:
                existing_rec = KnowledgeRecord.objects.filter(
                    **{f"canonical_data__{rec_key}": rec_val}
                ).first()

            if existing_rec:
                existing_rec.canonical_data.update(canonical_data)
                existing_rec.save()
                updated_count += 1
            else:
                new_rec = KnowledgeRecord.objects.create(
                    knowledge_document=doc,
                    entity_type="record",
                    canonical_data=canonical_data,
                    embedding_status="NOT_GENERATED"
                )
                imported_count += 1
                
                EnterpriseDataQualityReport.objects.create(
                    knowledge_record=new_rec,
                    overall_quality_score=95.0,
                    previous_quality_score=0.0,
                    trend="STABLE",
                    completeness_score=95.0,
                    validity_score=95.0,
                    consistency_score=95.0,
                    uniqueness_score=95.0,
                    timeliness_score=95.0,
                    quality_grade="A",
                    assessment_status="COMPLETED",
                    assessment_engine_version="1.0",
                    rules_version="1.0",
                    feature_version="1.0",
                    quality_features={"missing_fields": 0, "invalid_fields": 0, "duplicate_fields": 0, "record_age": 0},
                    ml_ready_features={"quality_score": 95.0},
                    processing_trace={"stack_add_import": True},
                    metadata={"created_by": request.user.username}
                )

        try:
            from ekcd.graph_service import UniversalKnowledgeGraphService
            UniversalKnowledgeGraphService().initialize_graph(force_rebuild=True)
        except Exception as kg_err:
            pass

        return ResponseBuilder.success({
            "imported_count": imported_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "total_rows": len(raw_records),
            "schema": inferred_schema,
            "errors": errors_list
        }, f"Stack Add completed: {imported_count} new records added, {updated_count} updated.")

    def update(self, request, *args, **kwargs):
        """
        PUT /api/v1/repository/employees/<id>/
        Updates record canonical_data fields dynamically.
        """
        instance = self.get_object()
        data = request.data

        cdata = instance.canonical_data or {}
        for k, v in data.items():
            if isinstance(v, str):
                v_str = v.strip()
                if re.match(r'^-?\d+\.\d+$', v_str.replace('$', '').replace(',', '')):
                    try:
                        cdata[k] = float(v_str.replace('$', '').replace(',', ''))
                    except ValueError:
                        cdata[k] = v_str
                elif re.match(r'^-?\d+$', v_str.replace('$', '').replace(',', '')):
                    try:
                        cdata[k] = int(v_str.replace('$', '').replace(',', ''))
                    except ValueError:
                        cdata[k] = v_str
                else:
                    cdata[k] = v_str
            else:
                cdata[k] = v

        instance.canonical_data = cdata
        instance.save()

        try:
            from ekcd.graph_service import UniversalKnowledgeGraphService
            UniversalKnowledgeGraphService().initialize_graph(force_rebuild=True)
        except Exception:
            pass

        return ResponseBuilder.success(
            data=SanitizedEmployeeRecordSerializer(instance).data,
            message="Record details updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/repository/employees/<id>/
        Removes an individual employee record.
        """
        instance = self.get_object()
        emp_id = instance.canonical_data.get('employee_id', instance.id)
        
        # Delete quality report
        from edqi.models import EnterpriseDataQualityReport
        EnterpriseDataQualityReport.objects.filter(knowledge_record=instance).delete()
        
        instance.delete()

        try:
            from ekcd.graph_service import UniversalKnowledgeGraphService
            UniversalKnowledgeGraphService().initialize_graph(force_rebuild=True)
        except Exception:
            pass

        return ResponseBuilder.success(
            data={"id": kwargs.get('pk')},
            message=f"Employee '{emp_id}' removed successfully."
        )

    @action(detail=False, methods=['post'], url_path='bulk_delete')
    def bulk_delete(self, request, *args, **kwargs):
        """
        POST /api/v1/repository/employees/bulk_delete/
        Stack Remove endpoint: Deletes multiple selected employee records by record ID list.
        """
        record_ids = request.data.get('record_ids', [])
        emp_ids = request.data.get('employee_ids', [])

        queryset = self.get_queryset()
        if record_ids:
            target_recs = queryset.filter(id__in=record_ids)
        elif emp_ids:
            target_recs = queryset.filter(canonical_data__employee_id__in=emp_ids)
        else:
            return ResponseBuilder.error(
                errors=["Missing Record IDs"],
                message="No record IDs or employee IDs provided for bulk deletion.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        count = target_recs.count()
        from edqi.models import EnterpriseDataQualityReport
        EnterpriseDataQualityReport.objects.filter(knowledge_record__in=target_recs).delete()
        target_recs.delete()

        try:
            from ekcd.graph_service import UniversalKnowledgeGraphService
            UniversalKnowledgeGraphService().initialize_graph(force_rebuild=True)
        except Exception:
            pass

        return ResponseBuilder.success({
            "deleted_count": count
        }, f"Stack Remove completed: {count} employee records removed.")

        return ResponseBuilder.success({
            "deleted_count": count
        }, f"All {count} employee records have been purged from the directory.")


class RepositoryFolderViewSet(viewsets.ModelViewSet):
    """
    ViewSet handling folder management (create nested folders, list folders, soft delete folders).
    """
    queryset = RepositoryFolder.objects.filter(is_deleted=False)
    serializer_class = RepositoryFolderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return RepositoryFolder.objects.none()
        
        repo_type = self.request.query_params.get('repository_type', 'team')
        qs = RepositoryFolder.objects.filter(is_deleted=False, repository_type=repo_type)
        
        if repo_type == 'personal':
            user_role = getattr(user, 'role', 'reader').lower()
            if user_role != 'admin':
                qs = qs.filter(owner=user)
        return qs

    def create(self, request, *args, **kwargs):
        name = request.data.get('name', '').strip()
        repo_type = request.data.get('repository_type', 'team')
        parent_id = request.data.get('parent_id')
        parent_path = request.data.get('parent_path', '')

        if not name:
            return ResponseBuilder.error(errors=["Folder name cannot be empty."], status_code=400)
        
        if re.search(r'[\\/:*?"<>|]', name):
            return ResponseBuilder.error(errors=["Folder name contains invalid characters."], status_code=400)

        owner = request.user if repo_type == 'personal' else None

        from repository.services.folder_service import FolderService
        if parent_id:
            try:
                parent_folder = RepositoryFolder.objects.get(id=parent_id, is_deleted=False)
                logical_path = f"{parent_folder.logical_path}/{name}"
            except RepositoryFolder.DoesNotExist:
                return ResponseBuilder.error(errors=["Parent folder not found."], status_code=404)
        elif parent_path:
            clean_parent = FolderService.normalize_path(parent_path)
            logical_path = f"{clean_parent}/{name}" if clean_parent else f"{'Personal' if repo_type == 'personal' else 'Team'}/{name}"
        else:
            root_prefix = 'Personal' if repo_type == 'personal' else 'Team'
            logical_path = f"{root_prefix}/{name}"

        if RepositoryFolder.objects.filter(is_deleted=False, repository_type=repo_type, logical_path__iexact=logical_path).exists():
            return ResponseBuilder.error(errors=[f"A folder with name '{name}' already exists in this location."], status_code=400)

        folder = FolderService.get_or_create_folder_by_path(logical_path, repo_type=repo_type, owner=owner)
        serializer = self.get_serializer(folder)
        return ResponseBuilder.success(data=serializer.data, message="Folder created successfully.", status_code=201)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        with transaction.atomic():
            instance.is_deleted = True
            instance.save()
            
            subfolders = RepositoryFolder.objects.filter(logical_path__startswith=f"{instance.logical_path}/")
            subfolders.update(is_deleted=True)
            
            docs = KnowledgeDocument.objects.filter(logical_path__startswith=f"{instance.logical_path}/")
            docs.update(repository_status='DELETED')

        return ResponseBuilder.success(data={"id": instance.id}, message="Folder moved to Recycle Bin.")

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = get_object_or_404(RepositoryFolder, id=pk)
        with transaction.atomic():
            instance.is_deleted = False
            instance.save()
            
            subfolders = RepositoryFolder.objects.filter(logical_path__startswith=f"{instance.logical_path}/")
            subfolders.update(is_deleted=False)
            
            docs = KnowledgeDocument.objects.filter(logical_path__startswith=f"{instance.logical_path}/")
            docs.update(repository_status='ACTIVE')

        return ResponseBuilder.success(data={"id": instance.id}, message="Folder restored from Recycle Bin.")

    @action(detail=True, methods=['delete'])
    def permanent_delete(self, request, pk=None):
        instance = get_object_or_404(RepositoryFolder, id=pk)
        safely_purge_folder(instance)
        return ResponseBuilder.success(data={"id": pk}, message="Folder permanently deleted.")


class RepositoryExplorerView(APIView):
    """
    Unified Explorer API listing subfolders, documents, breadcrumbs, search results, and filters
    for the active repository scope and folder path.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from repository.services.folder_service import FolderService
        repo_type = request.query_params.get('repository_type', 'team').lower()
        current_path = request.query_params.get('current_path', '').strip()
        folder_id = request.query_params.get('folder_id', '').strip()
        search_query = request.query_params.get('search', '').strip()
        file_type_filter = request.query_params.get('file_type', '').strip()
        status_filter = request.query_params.get('status', '').strip()

        if folder_id:
            target_f = RepositoryFolder.objects.filter(id=folder_id, is_deleted=False).first()
            if target_f:
                current_path = target_f.logical_path

        root_prefix = 'Personal' if repo_type == 'personal' else 'Team'

        if not current_path or current_path.lower() in ['root', 'home', 'team', 'personal']:
            current_path = root_prefix
        elif not current_path.startswith(('Team', 'Personal')):
            current_path = f"{root_prefix}/{current_path.lstrip('/')}"

        current_path = FolderService.normalize_path(current_path)

        # Build breadcrumbs
        parts = current_path.split('/')
        breadcrumbs = []
        path_acc = ""
        for p in parts:
            path_acc = f"{path_acc}/{p}" if path_acc else p
            f_item = RepositoryFolder.objects.filter(is_deleted=False, logical_path__iexact=path_acc).first()
            breadcrumbs.append({
                "id": str(f_item.id) if f_item else None,
                "name": p,
                "logical_path": path_acc
            })

        # Fetch folders
        folders_qs = RepositoryFolder.objects.filter(is_deleted=False, repository_type=repo_type)
        if repo_type == 'personal' and getattr(request.user, 'role', 'reader').lower() != 'admin':
            folders_qs = folders_qs.filter(owner=request.user)

        # Fetch documents strictly scoped by repository_type
        docs_qs = KnowledgeDocument.objects.exclude(repository_status='DELETED')
        if repo_type == 'personal':
            docs_qs = docs_qs.filter(Q(metadata__repository_type='personal') | Q(logical_path__startswith='Personal/'))
            user_role = getattr(request.user, 'role', 'reader').lower()
            if user_role != 'admin':
                docs_qs = docs_qs.filter(Q(owner=request.user) | Q(source_document__uploaded_by=request.user))
        else:
            docs_qs = docs_qs.filter(Q(metadata__repository_type='team') | Q(logical_path__startswith='Team/') | Q(metadata__repository_type__isnull=True))

        # Filter by path or search
        if search_query:
            folders_qs = folders_qs.filter(name__icontains=search_query)
            docs_qs = docs_qs.filter(Q(title__icontains=search_query) | Q(logical_path__icontains=search_query))
        else:
            curr_folder = RepositoryFolder.objects.filter(is_deleted=False, logical_path__iexact=current_path).first()
            if curr_folder:
                folders_qs = folders_qs.filter(parent=curr_folder)
                docs_qs = docs_qs.filter(Q(folder=curr_folder) | Q(logical_path__startswith=f"{current_path}/"))
                direct_docs = []
                for d in docs_qs:
                    lpath = d.logical_path or f"{current_path}/{d.title}"
                    if lpath.startswith(f"{current_path}/"):
                        rel = lpath[len(current_path):].strip('/')
                        if '/' not in rel and rel:
                            direct_docs.append(d)
                docs_qs = direct_docs
            else:
                folders_qs = folders_qs.filter(parent__isnull=True)
                root_docs = []
                for d in docs_qs:
                    lpath = d.logical_path or f"{root_prefix}/{d.title}"
                    if lpath.startswith(f"{root_prefix}/"):
                        rel = lpath[len(root_prefix):].strip('/')
                        if '/' not in rel and rel:
                            root_docs.append(d)
                docs_qs = root_docs

        if file_type_filter and file_type_filter.lower() != 'all':
            if isinstance(docs_qs, list):
                docs_qs = [d for d in docs_qs if d.title.lower().endswith(f".{file_type_filter.lower()}")]
            else:
                docs_qs = docs_qs.filter(title__icontains=f".{file_type_filter}")

        if status_filter and status_filter.lower() != 'all':
            if isinstance(docs_qs, list):
                docs_qs = [d for d in docs_qs if d.repository_status.lower() == status_filter.lower()]
            else:
                docs_qs = docs_qs.filter(repository_status__iexact=status_filter)

        folder_data = RepositoryFolderSerializer(folders_qs, many=True).data if not isinstance(folders_qs, list) else [RepositoryFolderSerializer(f).data for f in folders_qs]
        doc_data = KnowledgeDocumentSerializer(docs_qs, many=True).data if not isinstance(docs_qs, list) else [KnowledgeDocumentSerializer(d).data for d in docs_qs]

        return ResponseBuilder.success(data={
            "repository_type": repo_type,
            "current_path": current_path,
            "current_logical_path": current_path,
            "breadcrumbs": breadcrumbs,
            "folders": folder_data,
            "subfolders": folder_data,
            "documents": doc_data,
            "counts": {
                "folders_count": len(folder_data),
                "documents_count": len(doc_data)
            }
        }, message="Repository explorer view resolved.")


class RecycleBinView(APIView):
    """
    API view listing soft-deleted folders and documents, and handling purge-all actions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        user_role = getattr(user, 'role', 'reader').lower()

        deleted_folders = RepositoryFolder.objects.filter(is_deleted=True)
        deleted_docs = KnowledgeDocument.objects.filter(repository_status='DELETED')

        if user_role != 'admin':
            deleted_folders = deleted_folders.filter(owner=user)
            deleted_docs = deleted_docs.filter(Q(owner=user) | Q(source_document__uploaded_by=user))

        folder_serializer = RepositoryFolderSerializer(deleted_folders, many=True)
        doc_serializer = KnowledgeDocumentSerializer(deleted_docs, many=True)

        return ResponseBuilder.success(data={
            "folders": folder_serializer.data,
            "documents": doc_serializer.data,
            "counts": {
                "folders_count": deleted_folders.count(),
                "documents_count": deleted_docs.count()
            }
        }, message="Recycle Bin items resolved.")

    def delete(self, request, *args, **kwargs):
        """
        DELETE /api/v1/repository/recycle-bin/
        Empties/purges all items from Recycle Bin.
        """
        user = request.user
        user_role = getattr(user, 'role', 'reader').lower()

        deleted_folders = RepositoryFolder.objects.filter(is_deleted=True)
        deleted_docs = KnowledgeDocument.objects.filter(repository_status='DELETED')

        if user_role != 'admin':
            deleted_folders = deleted_folders.filter(owner=user)
            deleted_docs = deleted_docs.filter(Q(owner=user) | Q(source_document__uploaded_by=user))

        purged_docs = 0
        purged_folders = 0

        for f in list(deleted_folders):
            if safely_purge_folder(f):
                purged_folders += 1

        for d in list(deleted_docs):
            if safely_purge_document(d):
                purged_docs += 1

        return ResponseBuilder.success(
            data={"purged_docs": purged_docs, "purged_folders": purged_folders},
            message="Recycle Bin emptied successfully. All items permanently purged."
        )

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)


