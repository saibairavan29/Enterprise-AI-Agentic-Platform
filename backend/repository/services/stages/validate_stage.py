from repository.validators.repository_validator import RepositoryValidator

class ValidateStage:
    """
    Stage 1: Validate payload parameters before repository injection.
    """
    def execute(self, context):
        RepositoryValidator.validate_sync_payload(
            doc_id=context.get('document_id'),
            records=context.get('records'),
            metadata=context.get('metadata')
        )
        return context
