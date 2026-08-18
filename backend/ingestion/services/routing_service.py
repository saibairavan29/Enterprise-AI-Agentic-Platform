import time
import logging
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.services import BaseService
from ..models import Document
from ..router.dispatcher import ParserDispatcher

class IngestionRoutingService(BaseService):
    """
    Business service coordinating document routing in the ingestion pipeline:
    - Retreives Document records from PostgreSQL
    - Resolves the target parsing handler using ParserDispatcher
    - Transitions document status to 'VALIDATED'
    - Traces and logs performance parameters (Document ID, Parser Selected, Processing Time)
    """
    def process(self, document_id):
        start_time = time.perf_counter()
        
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            raise ValidationError(f"Document with ID {document_id} does not exist.")

        # Read stored ParserType classification
        parser_type_str = document.parser_type
        
        # Get target parser subclass from the Dispatcher
        parser_instance = ParserDispatcher.get_parser(parser_type_str)
        parser_name = parser_instance.__class__.__name__

        # Transition processing status to VALIDATED
        document.processing_status = 'VALIDATED'
        document.save()
        
        elapsed_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Standard Performance Log Trace
        self.logger.info(
            f"ROUTING | Document: {document.id} | "
            f"Parser: {parser_name} | "
            f"Status: VALIDATED | "
            f"Time: {elapsed_time_ms}ms"
        )
        
        return document
