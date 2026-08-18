import re
from datetime import datetime
from ..exceptions.metadata_exceptions import MetadataValidationException

class MetadataValidator:
    """
    Validator responsible for verifying the integrity of the compiled metadata payload:
    required fields, data types, timestamp isoformat, hashes formatting, and number bounds.
    """
    def validate(self, metadata_obj):
        """
        Validates the metadata dictionary object.
        Raises MetadataValidationException if any schema constraints are violated.
        """
        if not isinstance(metadata_obj, dict):
            raise MetadataValidationException("Metadata payload must be a dictionary.")

        # 1. Validate 'file' segment
        file_sec = metadata_obj.get("file")
        if not isinstance(file_sec, dict):
            raise MetadataValidationException("Metadata must contain a 'file' section.")
            
        req_file_fields = ["original_name", "stored_name", "size", "hash"]
        for f in req_file_fields:
            if file_sec.get(f) is None:
                raise MetadataValidationException(f"Missing required file metadata property: {f}")

        size = file_sec.get("size")
        if not isinstance(size, (int, float)) or size < 0:
            raise MetadataValidationException(f"File size must be a non-negative numeric value, got: {size}")

        file_hash = file_sec.get("hash")
        if not isinstance(file_hash, str) or not re.match(r"^[a-fA-F0-9]{64}$", file_hash):
            raise MetadataValidationException(f"Invalid SHA-256 hash formatting, got: {file_hash}")

        # 2. Validate 'lineage' segment
        lineage_sec = metadata_obj.get("lineage")
        if not isinstance(lineage_sec, dict):
            raise MetadataValidationException("Metadata must contain a 'lineage' section.")
        if lineage_sec.get("document_id") is None:
            raise MetadataValidationException("Missing required lineage metadata property: document_id")

        # 3. Validate 'processing' segment
        proc_sec = metadata_obj.get("processing")
        if not isinstance(proc_sec, dict):
            raise MetadataValidationException("Metadata must contain a 'processing' section.")
        
        req_proc_fields = ["metadata_version", "schema_version", "extraction_timestamp"]
        for f in req_proc_fields:
            if proc_sec.get(f) is None:
                raise MetadataValidationException(f"Missing required processing metadata property: {f}")

        extraction_time = proc_sec.get("extraction_timestamp")
        try:
            # Check ISO format compatibility (replacing Z with UTC offset if needed)
            datetime.fromisoformat(str(extraction_time).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise MetadataValidationException(f"Invalid ISO timestamp formatting inside extraction_timestamp, got: {extraction_time}")

        # 4. Validate OCR confidence metric ranges if populated
        ocr_sec = metadata_obj.get("ocr")
        if isinstance(ocr_sec, dict):
            conf = ocr_sec.get("confidence", {})
            if isinstance(conf, dict):
                avg_conf = conf.get("average")
                if avg_conf is not None:
                    if not isinstance(avg_conf, (int, float)) or avg_conf < 0.0 or avg_conf > 100.0:
                        raise MetadataValidationException(f"Average OCR confidence must be between 0.0 and 100.0, got: {avg_conf}")

        # 5. Validate 'statistics' segment
        stats_sec = metadata_obj.get("statistics")
        if not isinstance(stats_sec, dict):
            raise MetadataValidationException("Metadata must contain a 'statistics' section.")
        
        req_stats_fields = ["total_pages", "total_tables", "total_images", "total_words", "total_characters"]
        for sf in req_stats_fields:
            val = stats_sec.get(sf)
            if val is None:
                raise MetadataValidationException(f"Missing required statistics property: {sf}")
            if not isinstance(val, int) or val < 0:
                raise MetadataValidationException(f"Statistics field '{sf}' must be a non-negative integer, got: {val}")

        # 6. Validate 'quality' segment
        quality_sec = metadata_obj.get("quality")
        if not isinstance(quality_sec, dict):
            raise MetadataValidationException("Metadata must contain a 'quality' section.")
        
        completeness = quality_sec.get("metadata_completeness")
        if completeness is None or not isinstance(completeness, int) or completeness < 0 or completeness > 100:
            raise MetadataValidationException(f"Quality completeness must be an integer between 0 and 100, got: {completeness}")

        return True
PostgresMetadataValidator = MetadataValidator  # Alias for PostgreSQL database mapping validations
