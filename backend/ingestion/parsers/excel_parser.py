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
            # Open with context manager to auto-close and release locks on Windows
            with pd.ExcelFile(file_path, engine='openpyxl') as excel_file:
                sheet_names = excel_file.sheet_names
                
                for sheet in sheet_names:
                    # Read sheet data from the open file handle
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                    
                    # Cast to object type to successfully substitute NaN floating points with None
                    df_clean = df.astype(object).where(pd.notnull(df), None)
                    
                    # Extract records
                    records = df_clean.to_dict(orient='records')
                    sheets_data[sheet] = records
                    
                    # Reconstruct raw content text trace
                    all_text_elements.append(f"Worksheet: {sheet}")
                    for row in records:
                        row_values = [str(val) for val in row.values() if val is not None]
                        if row_values:
                            all_text_elements.append(" | ".join(row_values))

            full_text = "\n".join(all_text_elements)
            
            return {
                "content": full_text,
                "structured_data": sheets_data,
                "metadata": {
                    "sheets": sheet_names,
                    "sheet_count": len(sheet_names)
                },
                "parser_type": "EXCEL",
                "processing_status": "PARSED"
            }
            
        except Exception as e:
            logger.error(f"Failed parsing Excel file at {file_path}: {str(e)}", exc_info=True)
            raise e
