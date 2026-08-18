import json
import logging
from django.core.exceptions import ValidationError
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class APIParser(BaseDocumentParser):
    """
    Concrete parser converting REST API response bodies from JSON payloads.
    """
    def parse(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            data = json.loads(raw_text)
            
            return {
                "content": raw_text,
                "structured_data": data if isinstance(data, dict) else {"response": data},
                "metadata": {
                    "source": "REST_API_ENDPOINT"
                },
                "parser_type": "API",
                "processing_status": "PARSED"
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"REST API JSON conversion failed: {str(e)}")
            raise ValidationError(f"Invalid API response body payload: {str(e)}")
        except Exception as e:
            logger.error(f"Failed parsing API payload file at {file_path}: {str(e)}", exc_info=True)
            raise e
