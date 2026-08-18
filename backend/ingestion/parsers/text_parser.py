import logging
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class TextParser(BaseDocumentParser):
    """
    Concrete parser loading unstructured text files, cleaning spacing,
    and returning payload contents.
    """
    def parse(self, file_path):
        encodings = ['utf-8', 'latin-1', 'cp1252']
        raw_text = None
        detected_encoding = None

        # Try-except load loop
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    raw_text = f.read()
                detected_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if raw_text is None:
            raise ValueError(f"Could not decode text file using configured encodings: {encodings}")

        try:
            # Basic cleanup
            clean_text = raw_text.strip()
            
            return {
                "content": clean_text,
                "structured_data": {},
                "metadata": {
                    "encoding": detected_encoding,
                    "character_count": len(clean_text)
                },
                "parser_type": "TEXT",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing text file at {file_path}: {str(e)}", exc_info=True)
            raise e
