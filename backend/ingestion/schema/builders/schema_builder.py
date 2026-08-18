from ..schemas.enterprise_schema import EnterpriseCanonicalSchema

class SchemaBuilder:
    """
    Builder responsible for assembling mapped record parameters into a single
    generic Enterprise Canonical Record structure.
    """
    def build_record(self, document_id, entity_type, canonical_fields, additional_fields, metadata=None):
        """
        Builds a single canonical record.
        """
        record = EnterpriseCanonicalSchema.get_template()
        record["document_id"] = str(document_id) if document_id else ""
        record["entity_type"] = entity_type or "generic"
        record["canonical_fields"] = canonical_fields
        record["additional_fields"] = additional_fields
        record["metadata"] = metadata or {}
        return record
