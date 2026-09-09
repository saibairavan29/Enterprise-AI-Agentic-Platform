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
            from common.constants import PREVIEW_MAX_TEXT_BYTES
            clean_text = raw_text.strip()
            total_chars = len(clean_text)

            content_preview = clean_text
            if total_chars > PREVIEW_MAX_TEXT_BYTES:
                content_preview = clean_text[:PREVIEW_MAX_TEXT_BYTES] + "\n... [text content preview truncated due to file size]"
            
            return {
                "content": content_preview,
                "structured_data": {},
                "metadata": {
                    "encoding": detected_encoding,
                    "character_count": total_chars,
                    "preview_truncated": total_chars > PREVIEW_MAX_TEXT_BYTES
                },
                "parser_type": "TEXT",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing text file at {file_path}: {str(e)}", exc_info=True)
            raise e
