import os
import re
import logging
from typing import Optional, List, Tuple
from django.db import transaction
from repository.models import RepositoryFolder, KnowledgeDocument

logger = logging.getLogger('enterprise')

class FolderService:
    """
    Service for managing RepositoryFolder hierarchies, creating nested directories,
    resolving logical paths, and validating authorization.
    """

    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalizes logical repository paths.
        e.g. 'Team/Projects//Construction/' -> 'Team/Projects/Construction'
        """
        if not path:
            return ""
        # Replace backslashes with forward slashes
        clean_path = path.replace('\\', '/').strip('/')
        # Remove multiple consecutive slashes
        clean_path = re.sub(r'/+', '/', clean_path)
        return clean_path

    @classmethod
    def get_or_create_folder_by_path(cls, logical_path: str, repo_type: str = 'team', owner=None) -> Optional[RepositoryFolder]:
        """
        Recursively resolves or creates nested RepositoryFolder models for a given logical path string.
        e.g., 'Team/Projects/Construction/Riverside'
        """
        normalized = cls.normalize_path(logical_path)
        if not normalized:
            return None

        parts = normalized.split('/')
        # Strip root prefix 'Team' or 'Personal' if present in path string
        if parts[0].lower() in ['team', 'personal']:
            repo_type = parts[0].lower()
            parts = parts[1:]

        if not parts:
            return None

        current_parent = None
        current_path_acc = 'Team' if repo_type == 'team' else 'Personal'

        for part in parts:
            if not part.strip():
                continue
            folder_name = part.strip()
            current_path_acc = f"{current_path_acc}/{folder_name}"

            with transaction.atomic():
                folder, _ = RepositoryFolder.objects.get_or_create(
                    repository_type=repo_type,
                    parent=current_parent,
                    name=folder_name,
                    defaults={
                        'logical_path': current_path_acc,
                        'owner': owner if repo_type == 'personal' else None,
                        'is_deleted': False
                    }
                )
                if folder.is_deleted:
                    folder.is_deleted = False
                    folder.save()
            current_parent = folder

        return current_parent

    @classmethod
    def resolve_path(cls, logical_path: str, user=None) -> Tuple[Optional[RepositoryFolder], Optional[KnowledgeDocument], str]:
        """
        Resolves a logical path string to either a RepositoryFolder or a KnowledgeDocument.
        Returns tuple of (folder_obj, document_obj, error_msg).
        """
        normalized = cls.normalize_path(logical_path)
        if not normalized:
            return None, None, "Empty path provided."

        parts = normalized.split('/')
        repo_type = 'team'
        if parts[0].lower() in ['team', 'personal']:
            repo_type = parts[0].lower()

        # 1. Check exact match for KnowledgeDocument by logical_path
        doc = KnowledgeDocument.objects.exclude(repository_status='DELETED').filter(
            logical_path__iexact=normalized
        ).first()
        if doc:
            # Check user authorization
            if repo_type == 'personal' and user and user.is_authenticated:
                user_role = getattr(user, 'role', 'reader').lower()
                if user_role != 'admin' and doc.owner != user and (doc.source_document and doc.source_document.uploaded_by != user):
                    return None, None, "You do not have permission to access this repository item."
            return None, doc, ""

        # 2. Check exact match for RepositoryFolder by logical_path
        folder = RepositoryFolder.objects.filter(
            is_deleted=False,
            logical_path__iexact=normalized
        ).first()
        if folder:
            if repo_type == 'personal' and user and user.is_authenticated:
                user_role = getattr(user, 'role', 'reader').lower()
                if user_role != 'admin' and folder.owner != user:
                    return None, None, "You do not have permission to access this repository item."
            return folder, None, ""

        return None, None, "Repository path not found."
