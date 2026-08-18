import json
import logging
from django.core.exceptions import ValidationError
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class JSONParser(BaseDocumentParser):
    """
    Concrete parser loading JSON payload documents, preserving nesting,
    and validating formatting.
    """
    def parse(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            # Attempt to decode JSON structures
            data = json.loads(raw_text)
            
            return {
                "content": raw_text,
                "structured_data": data if isinstance(data, dict) else {"data": data},
                "metadata": {
                    "is_nested": any(isinstance(val, (dict, list)) for val in data.values()) if isinstance(data, dict) else False
                },
                "parser_type": "JSON",
                "processing_status": "PARSED"
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON validation failed for document at {file_path}: {str(e)}")
            raise ValidationError(f"Invalid JSON file format: {str(e)}")
        except Exception as e:
            logger.error(f"Failed parsing JSON file at {file_path}: {str(e)}", exc_info=True)
            raise e
