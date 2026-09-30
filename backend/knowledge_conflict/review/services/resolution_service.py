import time
import logging
from datetime import datetime
from django.db import transaction
from repository.models import KnowledgeDocumentVersion, KnowledgeRecord
from ...exceptions.exceptions import KnowledgeConflictException

logger = logging.getLogger('enterprise')

class ResolutionResult:
    """
    Data Transfer Object (DTO) capturing conflict resolution outputs.
    """
    def __init__(self, status: str, old_version: int, new_version: int, 
                 document_id: str, review_id: str, execution_time: float, warnings: list = None):
        self.status = status
        self.old_version = old_version
        self.new_version = new_version
        self.document_id = document_id
        self.review_id = review_id
        self.execution_time = execution_time
        self.warnings = warnings or []

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "document_id": str(self.document_id) if self.document_id else None,
            "review_id": str(self.review_id),
            "execution_time": self.execution_time,
            "warnings": self.warnings
        }


class ResolutionService:
    """
    Business service executing updates to the Knowledge Repository based on review resolutions.
    Integrates back-reference version tracking links.
    """
    def resolve_conflict(self, conflict, resolution_type: str, user, review_id: str, 
                         custom_edit_data: dict = None) -> ResolutionResult:
        start_time = time.time()
        
        # Pull document references
        src_doc = conflict.source_document
        tgt_doc = conflict.target_document
        
        old_ver = src_doc.current_version
        new_ver = old_ver
        doc_id = src_doc.id
        
        logger.info(f"Executing resolution '{resolution_type}' for Conflict {str(conflict.conflict_id)[:8]} (Review: {review_id})")
        
        try:
            with transaction.atomic():
                if resolution_type == 'KEEP_SOURCE':
                    # Keep source (uploaded document), archive target (existing document)
                    new_ver = src_doc.current_version
                    doc_id = src_doc.id
                    
                    if tgt_doc:
                        tgt_doc.repository_status = 'ARCHIVED'
                        tgt_doc.save(update_fields=['repository_status'])
                    
                    # Log immutable version snapshot
                    KnowledgeDocumentVersion.objects.create(
                        knowledge_document=src_doc,
                        version=new_ver,
                        raw_content=src_doc.raw_content,
                        checksum=f"link-{review_id}",
                        change_summary={
                            "previous_version": old_ver,
                            "new_version": new_ver,
                            "resolution": "KEEP_SOURCE",
                            "review_id": str(review_id),
                            "reason": f"Kept uploaded file {src_doc.title}, archived conflicting file {tgt_doc.title if tgt_doc else ''}."
                        }
                    )

                elif resolution_type == 'KEEP_TARGET':
                    # Keep target (existing document), archive source (uploaded document)
                    new_ver = tgt_doc.current_version if tgt_doc else old_ver
                    doc_id = tgt_doc.id if tgt_doc else src_doc.id
                    
                    if src_doc:
                        src_doc.repository_status = 'ARCHIVED'
                        src_doc.save(update_fields=['repository_status'])
                    
                    if tgt_doc:
                        KnowledgeDocumentVersion.objects.create(
                            knowledge_document=tgt_doc,
                            version=new_ver,
                            raw_content=tgt_doc.raw_content,
                            checksum=f"link-{review_id}",
                            change_summary={
                                "previous_version": tgt_doc.current_version,
                                "new_version": new_ver,
                                "resolution": "KEEP_TARGET",
                                "review_id": str(review_id),
                                "reason": f"Kept existing file {tgt_doc.title}, archived uploaded file {src_doc.title}."
                            }
                        )

                elif resolution_type == 'MERGE':
                    # Merge content: create combined records copy on source document
                    new_ver = src_doc.current_version + 1
                    doc_id = src_doc.id
                    
                    # Log version snapshot representing merged state
                    KnowledgeDocumentVersion.objects.create(
                        knowledge_document=src_doc,
                        version=new_ver,
                        raw_content=f"{src_doc.raw_content}\n\n[Merged Content from {tgt_doc.title}]:\n{tgt_doc.raw_content}",
                        checksum=f"link-{review_id}",
                        change_summary={
                            "previous_version": src_doc.current_version,
                            "new_version": new_ver,
                            "resolution": "MERGE",
                            "review_id": str(review_id),
                            "reason": "Merged record sets."
                        }
                    )
                    src_doc.current_version = new_ver
                    src_doc.save(update_fields=['current_version'])

                elif resolution_type == 'MANUAL_EDIT':
                    # Manually update source or target record canonical data fields
                    new_ver = src_doc.current_version + 1
                    doc_id = src_doc.id
                    
                    # Apply custom data modifications if passed
                    if custom_edit_data:
                        # Find record matches inside source doc
                        recs = KnowledgeRecord.objects.filter(knowledge_document=src_doc)
                        for r in recs:
                            r.canonical_data.update(custom_edit_data)
                            r.save(update_fields=['canonical_data'])
                            
                    KnowledgeDocumentVersion.objects.create(
                        knowledge_document=src_doc,
                        version=new_ver,
                        raw_content=src_doc.raw_content,
                        checksum=f"link-{review_id}",
                        change_summary={
                            "previous_version": src_doc.current_version,
                            "new_version": new_ver,
                            "resolution": "MANUAL_EDIT",
                            "review_id": str(review_id),
                            "custom_fields": list(custom_edit_data.keys()) if custom_edit_data else []
                        }
                    )
                    src_doc.current_version = new_ver
                    src_doc.save(update_fields=['current_version'])

                elif resolution_type == 'IGNORE':
                    # Ignore the false positive candidate (Old and new versions stay identical)
                    new_ver = old_ver
                    doc_id = src_doc.id
                    
                else:
                    raise KnowledgeConflictException(f"Unsupported resolution strategy action type: {resolution_type}")
                    
        except Exception as e:
            logger.error(f"Resolution transaction execution failed: {str(e)}", exc_info=True)
            raise KnowledgeConflictException(f"Failed to execute repository resolution: {str(e)}")
            
        elapsed_time = time.time() - start_time
        
        return ResolutionResult(
            status="SUCCESS",
            old_version=old_ver,
            new_version=new_ver,
            document_id=doc_id,
            review_id=review_id,
            execution_time=round(elapsed_time, 4)
        )
