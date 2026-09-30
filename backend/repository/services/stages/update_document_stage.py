from django.utils import timezone
from repository.repositories.document_repository import DocumentRepository
from common.json_utils import enforce_json_boundary
from common.path_utils import get_file_type_folder

class UpdateDocumentStage:
    """
    Stage 5: Create or update the KnowledgeDocument database entry 
    with current version, metadata, text content, and aggregate statistics.
    """
    def __init__(self):
        self.doc_repo = DocumentRepository()

    def execute(self, context):
        existing_doc = context.get('existing_doc')
        source_doc = context.get('source_doc')
        title = context.get('title')
        version = context.get('version', 1)
        raw_metadata = context.get('metadata', {})
        if not isinstance(raw_metadata, dict):
            raw_metadata = {}
        metadata = enforce_json_boundary(raw_metadata, label="KnowledgeDocument.metadata")

        repo_type = 'team'
        folder_id = None
        folder_obj = None
        target_path = ""
        owner_obj = source_doc.uploaded_by if source_doc else context.get('user')

        t_log_path = ""
        r_rel_path = ""
        if source_doc and source_doc.metadata and isinstance(source_doc.metadata, dict):
            s_meta = source_doc.metadata
            repo_type = s_meta.get("repository_type", repo_type)
            folder_id = s_meta.get("folder_id")
            t_log_path = s_meta.get("target_logical_path") or ""
            r_rel_path = s_meta.get("relative_path") or ""

        if not folder_id and metadata and isinstance(metadata, dict):
            repo_type = metadata.get("repository_type", repo_type)
            folder_id = metadata.get("folder_id")
            if not t_log_path:
                t_log_path = metadata.get("target_logical_path") or ""
            if not r_rel_path:
                r_rel_path = metadata.get("relative_path") or ""

        clean_title = title.split('/')[-1].split('\\')[-1]

        # Ensure Gmail ingestion documents are routed to Team/enterprise_ingestion_test_pack/<type>/<filename>
        is_gmail = False
        if source_doc and source_doc.metadata and isinstance(source_doc.metadata, dict):
            if source_doc.metadata.get("gmail_source") == "gmail_imap" or source_doc.metadata.get("source") == "gmail_imap":
                is_gmail = True
        elif metadata and isinstance(metadata, dict):
            if metadata.get("gmail_source") == "gmail_imap" or metadata.get("source") == "gmail_imap":
                is_gmail = True

        if is_gmail:
            fn = source_doc.original_name if source_doc else clean_title
            mime = source_doc.mime_type if source_doc else ""
            ptype = source_doc.parser_type if source_doc else ""
            folder_name = get_file_type_folder(fn, mime, ptype)
            t_log_path = f"Team/enterprise_ingestion_test_pack/{folder_name}/{clean_title}"
            r_rel_path = f"enterprise_ingestion_test_pack/{folder_name}/{clean_title}"
            if isinstance(metadata, dict):
                metadata["target_logical_path"] = t_log_path
                metadata["relative_path"] = r_rel_path
            if source_doc and isinstance(source_doc.metadata, dict):
                source_doc.metadata["target_logical_path"] = t_log_path
                source_doc.metadata["relative_path"] = r_rel_path
                source_doc.save()

        t_log_path = t_log_path.replace('\\', '/').strip('/')
        r_rel_path = r_rel_path.replace('\\', '/').strip('/')

        if t_log_path and (t_log_path.startswith('Team/') or t_log_path.startswith('Personal/')):
            target_path = t_log_path
        elif t_log_path and r_rel_path:
            # Strip redundant leading folder segment if it matches trailing component of t_log_path
            r_parts = r_rel_path.split('/')
            t_parts = t_log_path.split('/')
            if len(r_parts) > 1 and t_parts[-1].lower() == r_parts[0].lower():
                r_rel_path = "/".join(r_parts[1:])

            if r_rel_path == t_log_path or r_rel_path.startswith(f"{t_log_path}/"):
                target_path = r_rel_path
            else:
                target_path = f"{t_log_path}/{r_rel_path}"
        elif r_rel_path:
            target_path = r_rel_path
        else:
            target_path = t_log_path

        from repository.models import RepositoryFolder
        clean_title = title.split('/')[-1].split('\\')[-1]

        if folder_id:
            parent_f = RepositoryFolder.objects.filter(id=folder_id, is_deleted=False).first()
            if parent_f:
                folder_obj = parent_f
                repo_type = parent_f.repository_type
                if r_rel_path:
                    clean_r = r_rel_path.replace('\\', '/').strip('/')
                    if clean_r.startswith(f"{parent_f.logical_path}/"):
                        target_path = clean_r
                    else:
                        # Strip redundant leading folder segment if it matches parent folder name
                        parent_name = parent_f.name.strip()
                        r_parts = clean_r.split('/')
                        if len(r_parts) > 1 and r_parts[0].lower() == parent_name.lower():
                            clean_r = "/".join(r_parts[1:])
                        target_path = f"{parent_f.logical_path}/{clean_r}"
                elif t_log_path:
                    clean_rel = t_log_path.replace('\\', '/').strip('/')
                    if clean_rel.endswith(f"/{clean_title}"):
                        target_path = clean_rel
                    else:
                        target_path = f"{clean_rel}/{clean_title}"
                else:
                    target_path = f"{parent_f.logical_path}/{clean_title}"

        target_path = target_path.replace('\\', '/').strip('/')

        if not target_path:
            root_prefix = 'Personal' if repo_type == 'personal' else 'Team'
            target_path = f"{root_prefix}/{clean_title}"
        elif not target_path.startswith(('Team/', 'Personal/')):
            root_prefix = 'Personal' if repo_type == 'personal' else 'Team'
            target_path = f"{root_prefix}/{target_path.lstrip('/')}"

        if not target_path.endswith(f"/{clean_title}") and target_path != clean_title:
            target_path = f"{target_path}/{clean_title}"

        # Resolve or create parent folder structure if target path has subdirectories
        from repository.services.folder_service import FolderService
        parent_path = "/".join(target_path.split('/')[:-1])
        if parent_path and parent_path not in ['Team', 'Personal']:
            if not folder_obj or folder_obj.logical_path != parent_path:
                folder_obj = FolderService.get_or_create_folder_by_path(parent_path, repo_type=repo_type, owner=owner_obj)

        # Get raw content from parser result or source metadata
        raw_content = ""
        if context.get('raw_content'):
            raw_content = context['raw_content']
        elif hasattr(context, 'parser_result') and context.parser_result:
            raw_content = context.parser_result.get('content', '')
            
        record_count = len(context.get('records', []))
        repository_size = context.get('repository_size', 0)

        if existing_doc:
            existing_doc.title = title
            existing_doc.current_version = version
            existing_doc.repository_status = 'ACTIVE'
            existing_doc.metadata = metadata
            existing_doc.raw_content = raw_content
            existing_doc.record_count = record_count
            existing_doc.version_count = version
            existing_doc.last_sync = timezone.now()
            existing_doc.repository_size = repository_size
            existing_doc.folder = folder_obj
            existing_doc.logical_path = target_path
            if owner_obj:
                existing_doc.owner = owner_obj
            
            # Save using repository
            self.doc_repo.save(existing_doc)
            context['knowledge_document'] = existing_doc
        else:
            # Create a brand new active KnowledgeDocument
            new_doc = self.doc_repo.create(
                source_document=source_doc,
                title=title,
                current_version=version,
                repository_status='ACTIVE',
                metadata=metadata,
                raw_content=raw_content,
                record_count=record_count,
                version_count=version,
                last_sync=timezone.now(),
                repository_size=repository_size
            )
            new_doc.folder = folder_obj
            new_doc.logical_path = target_path
            new_doc.owner = owner_obj
            new_doc.save()
            context['knowledge_document'] = new_doc

        return context
