class ResponseBuilder:
    """
    Builder responsible for wrapping the standardized record,
    compiling the standardization report with field changes, and passing metadata.
    """
    def build_response(self, standardized_rec, metadata, statistics, changes_list, warnings=None, errors=None):
        """
        Assembles response components into the final output structure.
        """
        if warnings is None:
            warnings = []
        if errors is None:
            errors = []

        return {
            "standardized_record": standardized_rec,
            "standardization_report": {
                "fields_processed": int(statistics.get("processed", 0)),
                "fields_standardized": len(changes_list),
                "fields_skipped": int(statistics.get("skipped", 0)),
                "fields_failed": int(statistics.get("failed", 0)),
                "execution_time": float(statistics.get("execution_time", 0.0)),
                "warnings": warnings,
                "errors": errors,
                "field_changes": changes_list,
                "standardization_version": "1.0"
            },
            "metadata": metadata or {}
        }
