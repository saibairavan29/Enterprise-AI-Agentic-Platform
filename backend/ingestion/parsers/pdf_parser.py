import fitz
import pdfplumber
import logging
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class PDFParser(BaseDocumentParser):
    """
    Concrete parser extracting digital text, ordering pages, extracting tabular frames
    using pdfplumber, and flagging scanned pages.
    """
    def parse(self, file_path):
        text_content = []
        page_texts = []
        all_tables = []
        is_scanned = False
        
        try:
            # 1. Open PyMuPDF to extract text & metadata
            with fitz.open(file_path) as doc:
                page_count = len(doc)
                metadata = {
                    "page_count": page_count,
                    "author": doc.metadata.get('author', ''),
                    "title": doc.metadata.get('title', ''),
                    "creator": doc.metadata.get('creator', ''),
                    "subject": doc.metadata.get('subject', '')
                }
                
                total_chars = 0
                for i in range(page_count):
                    page = doc[i]
                    txt = page.get_text() or ""
                    page_texts.append(txt)
                    text_content.append(txt)
                    total_chars += len(txt.strip())

                # If character count is extremely low relative to pages, classify as scanned document
                if page_count > 0 and (total_chars / page_count) < 20:
                    is_scanned = True
                
                metadata["is_scanned"] = is_scanned

            # 2. Open pdfplumber to extract structured tables
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            # Clean empty headers/none values in tabular structures
                            cleaned_table = [
                                [str(cell).strip() if cell is not None else "" for cell in row]
                                for row in table if any(cell is not None for cell in row)
                            ]
                            all_tables.append({
                                "page": idx + 1,
                                "data": cleaned_table
                            })

            full_text = "\n\n".join(text_content)
            
            return {
                "content": full_text,
                "structured_data": {
                    "pages": page_texts,
                    "tables": all_tables
                },
                "metadata": metadata,
                "parser_type": "PDF",
                "processing_status": "PARSED"
            }

        except Exception as e:
            logger.error(f"Failed parsing PDF file at {file_path}: {str(e)}", exc_info=True)
            raise e
