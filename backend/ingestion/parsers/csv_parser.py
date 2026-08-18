import pandas as pd
import logging
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class CSVParser(BaseDocumentParser):
    """
    Concrete parser extracting records from CSV files. Resolves encodings
    and handles missing values.
    """
    def parse(self, file_path):
        encodings = ['utf-8', 'latin-1', 'cp1252']
        df = None
        detected_encoding = None

        # 1. Encoding Detection fallback loop
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                detected_encoding = encoding
                break
            except (UnicodeDecodeError, ValueError):
                continue
                
        if df is None:
            # Final raw fallback
            raise ValueError(f"Could not decode CSV file using standard encodings: {encodings}")

        try:
            # 2. Null Value handling - map NaNs to None for clean JSON Serialization
            df_clean = df.astype(object).where(pd.notnull(df), None)
            records = df_clean.to_dict(orient='records')
            
            # Reconstruct plaintext representation
            all_text_elements = []
            for row in records:
                row_values = [str(val) for val in row.values() if val is not None]
                if row_values:
                    all_text_elements.append(" | ".join(row_values))
                    
            full_text = "\n".join(all_text_elements)
            
            return {
                "content": full_text,
                "structured_data": {
                    "records": records
                },
                "metadata": {
                    "encoding": detected_encoding,
                    "row_count": len(records),
                    "column_count": len(df.columns)
                },
                "parser_type": "CSV",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing CSV file at {file_path}: {str(e)}", exc_info=True)
            raise e
