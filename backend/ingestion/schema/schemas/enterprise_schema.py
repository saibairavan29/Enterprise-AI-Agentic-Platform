CANONICAL_FIELDS = {
    "employee_id": None,
    "department": None,
    "phone_number": None,
    "email": None,
    "joining_date": None,
    "salary": None
}

class EnterpriseCanonicalSchema:
    """
    Single source of truth defining the standard canonical structure
    for all enterprise document entities.
    """
    @staticmethod
    def get_template():
        """
        Returns a fresh generic canonical dictionary template.
        """
        return {
            "document_id": "",
            "entity_type": "generic",
            "canonical_fields": dict(CANONICAL_FIELDS),
            "relationships": {},
            "additional_fields": {},
            "metadata": {}
        }
