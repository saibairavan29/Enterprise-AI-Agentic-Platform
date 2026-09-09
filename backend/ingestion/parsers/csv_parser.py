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
            total_rows = len(df)
            total_cols = len(df.columns)
            headers = [str(col) for col in df.columns]

            # 2. Null Value handling & Memory-Safe Preview Extraction
            from common.constants import PREVIEW_MAX_RECORDS, PREVIEW_MAX_TEXT_BYTES
            
            # Slice sample preview for structured data representation to prevent memory overflow
            df_preview = df.iloc[:PREVIEW_MAX_RECORDS]
            df_clean = df_preview.astype(object).where(pd.notnull(df_preview), None)
            records = df_clean.to_dict(orient='records')
            
            # Reconstruct plaintext representation (capped to PREVIEW_MAX_TEXT_BYTES)
            all_text_elements = []
            text_size = 0
            for row in records:
                row_values = [str(val) for val in row.values() if val is not None]
                if row_values:
                    line_str = " | ".join(row_values)
                    all_text_elements.append(line_str)
                    text_size += len(line_str)
                    if text_size > PREVIEW_MAX_TEXT_BYTES:
                        all_text_elements.append("... [preview content truncated due to file size]")
                        break
                    
            full_text = "\n".join(all_text_elements)
            
            return {
                "content": full_text,
                "structured_data": {
                    "records": records,
                    "preview_truncated": total_rows > PREVIEW_MAX_RECORDS,
                    "total_records": total_rows
                },
                "metadata": {
                    "encoding": detected_encoding,
                    "row_count": total_rows,
                    "column_count": total_cols,
                    "headers": headers,
                    "preview_row_count": len(records)
                },
                "parser_type": "CSV",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing CSV file at {file_path}: {str(e)}", exc_info=True)
            raise e
