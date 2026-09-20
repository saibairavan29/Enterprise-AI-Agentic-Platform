import hashlib
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.services import BaseService
from ..models import Document
from common.validators import validate_file_size, validate_file_extension, validate_mime_type
from common.parser_types import ParserType

class DocumentUploadService(BaseService):
    """
    Business service responsible for handling raw file uploads:
    - Running structured validation pipeline (Exists -> Size -> Extension -> Magic Bytes -> Duplicate Hash check)
    - Determining standard MIME and system ParserType mappings
    - Storing files in Uploads/raw/ and saving metadata records in DB
    - Writing standard audit log messages
    """
    def process(self, file_obj, user):
        # 1. File Exists Check
        if not file_obj or file_obj.size == 0:
            raise ValidationError("No file uploaded or file content is empty.")
            
        # 2. Size Check
        validate_file_size(file_obj)
        
        # 3. Extension Check
        ext = validate_file_extension(file_obj.name)
        
        # 4. MIME Signature Check (Magic Bytes)
        validate_mime_type(file_obj, ext)
        
        # 5. Generate SHA-256 Hash incrementally (memory-safe chunking)
        sha256 = hashlib.sha256()
        for chunk in file_obj.chunks(chunk_size=128 * 1024):
            sha256.update(chunk)
        file_hash = sha256.hexdigest()
        file_obj.seek(0)
        
        # 6. Clean up previous/existing uploads with identical file name or hash for smooth re-uploading
        from django.db import transaction
        existing_docs = list(Document.objects.filter(file_hash=file_hash))
        for e_doc in existing_docs:
            self.logger.info(f"Purging existing document record {e_doc.id} with name {file_obj.name} for fresh re-upload.")
            try:
                with transaction.atomic(savepoint=True):
                    e_doc.delete()
            except Exception as del_err:
                self.logger.warning(f"Could not purge existing doc {e_doc.id}: {del_err}")
        
        # Determine standard MIME string mapping
        mime_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'csv': 'text/csv',
            'txt': 'text/plain',
            'json': 'application/json'
        }
        mime_type = mime_map.get(ext, 'application/octet-stream')
        
        # Determine ParserType enum mapping
        parser_map = {
            'pdf': ParserType.PDF,
            'xlsx': ParserType.EXCEL,
            'xls': ParserType.EXCEL,
            'csv': ParserType.CSV,
            'json': ParserType.JSON,
            'txt': ParserType.TEXT,
            'png': ParserType.IMAGE,
            'jpg': ParserType.IMAGE,
            'jpeg': ParserType.IMAGE
        }
        parser_type = parser_map.get(ext, ParserType.TEXT)
        
        # 7. Save Model to Database (files will default upload inside raw/ as defined in model)
        document = Document(
            uploaded_by=user,
            file=file_obj,
            file_hash=file_hash,
            original_name=file_obj.name,
            file_size=file_obj.size,
            mime_type=mime_type,
            parser_type=parser_type.value,
            processing_status='UPLOADED',
            validation_status='pending'
        )
        document.save()
        
        # 8. Standard Audit Log Entry
        self.logger.info(
            f"AUDIT | User: {user.username} | "
            f"Filename: {document.original_name} | "
            f"Hash: {document.file_hash} | "
            f"Timestamp: {timezone.now().isoformat()}"
        )
        
        return document
