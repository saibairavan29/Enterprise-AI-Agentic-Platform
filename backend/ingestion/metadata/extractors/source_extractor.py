from django.utils import timezone
from .base import BaseExtractor

class SourceExtractor(BaseExtractor):
    """
    Extractor responsible for document source and governance metrics:
    source_type, source_system, uploaded_by, upload_method, received_timestamp,
    storage_location, and file_path.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "source_type": "UPLOAD",
            "source_system": "Enterprise Platform",
            "uploaded_by": None,
            "upload_method": "WEB",
            "received_timestamp": None,
            "storage_location": None,
            "file_path": None
        }

        if not doc_obj:
            return res

        # Resolve uploader user identifier
        uploaded_by_user = getattr(doc_obj, "uploaded_by", None)
        if uploaded_by_user:
            res["uploaded_by"] = str(getattr(uploaded_by_user, "id", uploaded_by_user))
        elif isinstance(doc_obj, dict):
            res["uploaded_by"] = str(doc_obj.get("uploaded_by", ""))

        # Resolve timestamp from CoreModel created_at field
        created_at = getattr(doc_obj, "created_at", None)
        if created_at:
            if hasattr(created_at, "isoformat"):
                res["received_timestamp"] = created_at.isoformat()
            else:
                res["received_timestamp"] = str(created_at)
        elif isinstance(doc_obj, dict) and doc_obj.get("created_at"):
            res["received_timestamp"] = doc_obj.get("created_at")
        else:
            res["received_timestamp"] = timezone.now().isoformat()

        # Resolve paths
        stored_path = None
        file_field = getattr(doc_obj, "file", None)
        if file_field and hasattr(file_field, "name"):
            stored_path = file_field.name
        elif isinstance(doc_obj, dict):
            stored_path = doc_obj.get("stored_name") or doc_obj.get("file_path")

        if stored_path:
            res["storage_location"] = f"Uploads/{stored_path}"
            res["file_path"] = f"Uploads/{stored_path}"

        return res
