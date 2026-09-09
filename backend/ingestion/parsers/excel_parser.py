import pandas as pd
import logging
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class ExcelParser(BaseDocumentParser):
    """
    Concrete parser extracting tabular sheet records from Excel documents
    preserving numerical/categorical datatypes.
    """
    def parse(self, file_path):
        sheets_data = {}
        all_text_elements = []
        
        try:
            from common.constants import PREVIEW_MAX_RECORDS, PREVIEW_MAX_TEXT_BYTES
            sheet_stats = {}
            text_size = 0

            # Open with context manager to auto-close and release locks on Windows
            with pd.ExcelFile(file_path, engine='openpyxl') as excel_file:
                sheet_names = excel_file.sheet_names
                
                for sheet in sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                    total_sheet_rows = len(df)
                    sheet_stats[sheet] = {
                        "row_count": total_sheet_rows,
                        "column_count": len(df.columns)
                    }
                    
                    df_preview = df.iloc[:PREVIEW_MAX_RECORDS]
                    df_clean = df_preview.astype(object).where(pd.notnull(df_preview), None)
                    records = df_clean.to_dict(orient='records')
                    sheets_data[sheet] = records
                    
                    # Reconstruct raw content text trace (capped)
                    if text_size < PREVIEW_MAX_TEXT_BYTES:
                        all_text_elements.append(f"Worksheet: {sheet}")
                        for row in records:
                            row_values = [str(val) for val in row.values() if val is not None]
                            if row_values:
                                line_str = " | ".join(row_values)
                                all_text_elements.append(line_str)
                                text_size += len(line_str)
                                if text_size > PREVIEW_MAX_TEXT_BYTES:
                                    all_text_elements.append("... [preview content truncated due to size]")
                                    break

            full_text = "\n".join(all_text_elements)
            
            return {
                "content": full_text,
                "structured_data": sheets_data,
                "metadata": {
                    "sheets": sheet_names,
                    "sheet_count": len(sheet_names),
                    "sheet_stats": sheet_stats
                },
                "parser_type": "EXCEL",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing Excel file at {file_path}: {str(e)}", exc_info=True)
            raise e
