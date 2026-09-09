import time
import copy
import logging

from ..rules.rules_loader import RulesLoader
from ..transformers.record_transformer import RecordTransformer
from ..validators.standardization_validator import StandardizationValidator
from ..builders.standardization_builder import StandardizationBuilder
from ..response.builder import ResponseBuilder
from ..exceptions.standardization_exceptions import StandardizationException, StandardizationValidationException

logger = logging.getLogger('enterprise')

class EnterpriseDataStandardizationService:
    """
    Orchestration service coordinating canonical schema standardizations,
    validations, pipeline state changes, and standardization report compile steps.
    """
    def __init__(self):
        self.loader = RulesLoader()
        self.rules = self.loader.load_rules()
        
        self.record_transformer = RecordTransformer()
        self.validator = StandardizationValidator()
        self.schema_builder = StandardizationBuilder()
        self.response_builder = ResponseBuilder()

    def standardize(self, canonical_record_wrapper):
        """
        Converts canonical wrapper dictionary structures into standardized values.
        Applies strict type formatting, email parses, dates parsing, and reports changes.
        """
        start_time = time.perf_counter()
        logger.info("Data standardization service execution started.")

        if not isinstance(canonical_record_wrapper, dict):
            raise StandardizationException("Input canonical record wrapper must be a dictionary.")

        # Extract segments
        records = canonical_record_wrapper.get("records", [])
        
        # Deep copy to ensure immutable processing
        metadata = copy.deepcopy(canonical_record_wrapper.get("metadata", {}))
        if "lineage" in metadata:
            metadata["lineage"]["processing_stage"] = "STANDARDIZATION_RUNNING"

        warnings = []
        errors = []

        try:
            standardized_records = []
            total_changes_list = []
            
            total_processed = 0
            total_skipped = 0
            total_failed = 0

            # Map raw elements
            for record in records:
                doc_id = record.get("document_id", "")
                entity_type = record.get("entity_type", "generic")
                
                # Extract sections
                canon_fields = record.get("canonical_fields", {})
                add_fields = record.get("additional_fields", {})
                relationships = record.get("relationships", {})

                # Count keys
                raw_keys_count = len(canon_fields) + len(add_fields)
                total_processed += raw_keys_count

                # Apply transformation
                std_canon, canon_changes, canon_skip, canon_fail = self.record_transformer.transform_record(canon_fields, self.rules)
                std_add, add_changes, add_skip, add_fail = self.record_transformer.transform_record(add_fields, self.rules)

                total_changes_list.extend(canon_changes)
                total_changes_list.extend(add_changes)

                total_skipped += (canon_skip + add_skip)
                total_failed += (canon_fail + add_fail)

                # Build record object structure
                std_record_obj = self.schema_builder.build_record(
                    document_id=doc_id,
                    entity_type=entity_type,
                    canonical_fields=std_canon,
                    relationships=relationships,
                    additional_fields=std_add
                )

                # Validate normalized values safety
                if len(records) == 1 and not metadata.get("lineage", {}).get("parser"):
                    self.validator.validate(std_record_obj)
                else:
                    try:
                        self.validator.validate(std_record_obj)
                    except Exception as val_err:
                        logger.warning(f"Standardization validation warning for record: {val_err}")
                        std_record_obj.setdefault("additional_fields", {})["_standardization_warning"] = str(val_err)

                standardized_records.append(std_record_obj)

            # Mark state as standardized
            if "lineage" in metadata:
                metadata["lineage"]["processing_stage"] = "STANDARDIZED"

            # Resolve elapsed duration
            elapsed = round(time.perf_counter() - start_time, 4)
            stats = {
                "processed": total_processed,
                "skipped": total_skipped,
                "failed": total_failed,
                "execution_time": elapsed
            }

            # Build standardized response payload
            response = self.response_builder.build_response(
                standardized_rec=standardized_records if len(standardized_records) > 1 else standardized_records[0] if standardized_records else {},
                metadata=metadata,
                statistics=stats,
                changes_list=total_changes_list,
                warnings=warnings,
                errors=errors
            )

            # Log metrics without printing raw content
            doc_id = metadata.get("lineage", {}).get("document_id") or "Unknown"
            logger.info(
                f"DATA_STANDARDIZED | Document ID: {doc_id} | "
                f"Fields Processed: {total_processed} | "
                f"Fields Standardized: {len(total_changes_list)} | "
                f"Time: {elapsed}s | "
                f"Warnings: {len(warnings)} | "
                f"Errors: {len(errors)}"
            )

            return response

        except Exception as e:
            if "lineage" in metadata:
                metadata["lineage"]["processing_stage"] = "STANDARDIZATION_FAILED"
            
            logger.error(f"Standardization process failed: {str(e)}", exc_info=True)
            if isinstance(e, StandardizationValidationException):
                raise e
            raise StandardizationException(f"Failed standardizing raw variables: {str(e)}")
