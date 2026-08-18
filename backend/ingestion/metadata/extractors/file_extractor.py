import os
from .base import BaseExtractor

class FileExtractor(BaseExtractor):
    """
    Extractor responsible for physical file metrics:
    size, hash, extension, mime_type, original filename, and stored path.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        if not doc_obj:
            return {
                "original_name": None,
                "stored_name": None,
                "extension": None,
                "mime_type": None,
                "size": None,
                "hash": None
            }

        # Resolve properties dynamically from model instances or direct dictionary keys (mock test friendly)
        orig_name = getattr(doc_obj, "original_name", None)
        if orig_name is None and isinstance(doc_obj, dict):
            orig_name = doc_obj.get("original_name")

        file_hash = getattr(doc_obj, "file_hash", None)
        if file_hash is None and isinstance(doc_obj, dict):
            file_hash = doc_obj.get("file_hash")

        file_size = getattr(doc_obj, "file_size", None)
        if file_size is None and isinstance(doc_obj, dict):
            file_size = doc_obj.get("file_size")

        mime_type = getattr(doc_obj, "mime_type", None)
        if mime_type is None and isinstance(doc_obj, dict):
            mime_type = doc_obj.get("mime_type")

        stored_name = None
        file_field = getattr(doc_obj, "file", None)
        if file_field and hasattr(file_field, "name"):
            stored_name = file_field.name
        elif isinstance(doc_obj, dict):
            stored_name = doc_obj.get("stored_name")

        ext = None
        if orig_name:
            ext = os.path.splitext(orig_name)[1].lower().replace(".", "")

        return {
            "original_name": orig_name,
            "stored_name": stored_name,
            "extension": ext or None,
            "mime_type": mime_type,
            "size": file_size,
            "hash": file_hash
        }
