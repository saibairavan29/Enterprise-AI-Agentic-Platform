class ResponseBuilder:
    """
    Builder responsible for compiling the final response dictionary wrapper,
    aggregating mapping statistics, and adding schema version headers.
    """
    def build_response(self, records_list, aggregated_metadata, execution_time=0.0, doc_id="unknown", entity_type="generic"):
        """
        Wraps records into a standardized canonical response structure.
        """
        total = aggregated_metadata.get("total_raw_fields", 0)
        mapped = aggregated_metadata.get("mapped_count", 0)
        unmapped = aggregated_metadata.get("unmapped_count", 0)
        
        duplicates = aggregated_metadata.get("duplicates", [])
        conflicts = aggregated_metadata.get("conflicts", [])
        
        # Determine warnings
        warnings = []
        if conflicts:
            warnings.append(f"Detected {len(conflicts)} mappings with conflicting raw values.")
        if duplicates:
            warnings.append(f"Detected {len(duplicates)} duplicate field entries.")

        # Compute accuracy (penalizes mapping conflicts)
        accuracy = 100.0
        if total > 0:
            accuracy = round((mapped / total) * 100.0, 2)

        return {
            "data": {
                "records": records_list
            },
            "records": records_list,
            "mapping_statistics": {
                "total_fields": total,
                "mapped_fields": mapped,
                "unmapped_fields": unmapped,
                "mapping_accuracy": accuracy,
                "duplicate_fields": duplicates,
                "conflicting_fields": [c["attempted_key"] for c in conflicts if isinstance(c, dict) and "attempted_key" in c],
                "warnings": warnings
            },
            "analytics_summary": {
                "records_mapped": len(records_list),
                "mapping_accuracy_percent": accuracy,
                "warnings": warnings,
                "execution_time_seconds": execution_time
            },
            "schema_information": {
                "schema_version": "1.0",
                "canonical_schema_version": "1.0",
                "document_id": doc_id,
                "entity_type": entity_type
            }
        }

    def build(self, mapped_records, metadata, execution_time=0.0, doc_id="unknown", entity_type="generic"):
        return self.build_response(mapped_records, metadata, execution_time, doc_id, entity_type)
