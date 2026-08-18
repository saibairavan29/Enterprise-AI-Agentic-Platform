class StandardizationBuilder:
    """
    Builder responsible for assembling standardized canonical record structures.
    """
    def build_record(self, document_id, entity_type, canonical_fields, relationships, additional_fields):
        """
        Assembles canonical parameters into a standardized record.
        """
        return {
            "document_id": str(document_id) if document_id else "",
            "entity_type": entity_type or "generic",
            "canonical_fields": canonical_fields,
            "relationships": relationships or {},
            "additional_fields": additional_fields or {}
        }
