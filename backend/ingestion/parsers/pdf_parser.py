import fitz
import pdfplumber
import logging
import os
import re
from PIL import Image
import io
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

def configure_pytesseract():
    """
    Attempts to locate tesseract executable on Windows system if not in PATH.
    """
    try:
        import pytesseract
        import shutil
        if shutil.which("tesseract"):
            return True
        possible_paths = [
            r"C:\Users\yogeshwaran\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            r"C:\tools\tesseract\tesseract.exe",
            os.environ.get("TESSERACT_PATH", "")
        ]
        for p in possible_paths:
            if p and os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                tess_dir = os.path.dirname(p)
                tessdata_dir = os.path.join(tess_dir, "tessdata")
                if os.path.exists(tessdata_dir):
                    os.environ["TESSDATA_PREFIX"] = tessdata_dir
                return True
    except Exception as e:
        logger.debug(f"Error configuring pytesseract: {e}")
    return False

class PDFParser(BaseDocumentParser):
    """
    Concrete parser extracting digital text, ordering pages, extracting tabular frames
    using pdfplumber, and executing page rendering OCR for scanned documents.
    """
    def parse(self, file_path):
        text_content = []
        page_texts = []
        all_tables = []
        is_scanned = False
        
        pdf_text_extracted = False
        pdf_text_length = 0
        ocr_attempted = False
        ocr_pages_attempted = 0
        ocr_success = False
        ocr_text_length = 0
        ocr_error = None

        filename = os.path.basename(file_path)
        base_name, _ = os.path.splitext(filename)

        try:
            # 1. Open PyMuPDF to extract digital text & metadata
            with fitz.open(file_path) as doc:
                page_count = len(doc)
                metadata = {
                    "page_count": page_count,
                    "author": doc.metadata.get('author', '') if doc.metadata else '',
                    "title": doc.metadata.get('title', '') if doc.metadata else '',
                    "creator": doc.metadata.get('creator', '') if doc.metadata else '',
                    "subject": doc.metadata.get('subject', '') if doc.metadata else ''
                }
                
                total_chars = 0
                for i in range(page_count):
                    page = doc[i]
                    txt = page.get_text() or ""
                    page_texts.append(txt)
                    text_content.append(txt)
                    total_chars += len(txt.strip())

                pdf_text_length = total_chars
                pdf_text_extracted = (total_chars >= 20)

                # 2. Check if digital text layer is insufficient -> Trigger Page Pixmap Rendering & OCR Fallback
                if page_count > 0 and (total_chars / page_count) < 20:
                    is_scanned = True
                    ocr_attempted = True
                    ocr_pages_attempted = page_count

                    tess_available = configure_pytesseract()
                    ocr_page_texts = []

                    try:
                        import pytesseract
                        for i in range(page_count):
                            page = doc[i]
                            pix = page.get_pixmap(dpi=150)
                            img_data = pix.tobytes("png")
                            img = Image.open(io.BytesIO(img_data))
                            
                            tess_txt = ""
                            if tess_available:
                                try:
                                    tess_txt = pytesseract.image_to_string(img) or ""
                                except Exception as t_err:
                                    ocr_error = str(t_err)
                                    logger.warning(f"PyTesseract execution failed: {t_err}")
                            
                            if tess_txt.strip():
                                ocr_page_texts.append(tess_txt.strip())

                        if ocr_page_texts:
                            ocr_success = True
                            page_texts = ocr_page_texts
                            text_content = ocr_page_texts
                            full_ocr_str = "\n\n".join(ocr_page_texts)
                            ocr_text_length = len(full_ocr_str)
                        else:
                            if not ocr_error:
                                ocr_error = "Tesseract executable not found or image text unreadable"

                    except Exception as ocr_err:
                        ocr_error = str(ocr_err)
                        logger.warning(f"PyMuPDF OCR fallback encountered issue: {ocr_err}")

                metadata["is_scanned"] = is_scanned
                metadata["pdf_text_extracted"] = pdf_text_extracted
                metadata["pdf_text_length"] = pdf_text_length
                metadata["ocr_attempted"] = ocr_attempted
                metadata["ocr_pages_attempted"] = ocr_pages_attempted
                metadata["ocr_success"] = ocr_success
                metadata["ocr_text_length"] = ocr_text_length
                metadata["ocr_error"] = ocr_error

            # 3. Open pdfplumber to extract structured tables (if present, capped to first 50 pages)
            try:
                with pdfplumber.open(file_path) as pdf:
                    max_plumber_pages = min(len(pdf.pages), 50)
                    for idx in range(max_plumber_pages):
                        page = pdf.pages[idx]
                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                cleaned_table = [
                                    [str(cell).strip() if cell is not None else "" for cell in row]
                                    for row in table if any(cell is not None for cell in row)
                                ]
                                all_tables.append({
                                    "page": idx + 1,
                                    "data": cleaned_table
                                })
                            if len(all_tables) >= 50:
                                break
                        if len(all_tables) >= 50:
                            break
            except Exception as plumber_err:
                logger.debug(f"pdfplumber table extraction skipped: {plumber_err}")

            from common.constants import PREVIEW_MAX_TEXT_BYTES
            full_text = "\n\n".join([t.strip() for t in text_content if t.strip()])
            if len(full_text) > PREVIEW_MAX_TEXT_BYTES:
                full_text = full_text[:PREVIEW_MAX_TEXT_BYTES] + "\n\n... [pdf text preview truncated due to file size]"
            
            return {
                "content": full_text,
                "structured_data": {
                    "pages": page_texts[:500],
                    "tables": all_tables,
                    "preview_truncated": len(page_texts) > 500
                },
                "metadata": metadata,
                "parser_type": "PDF",
                "processing_status": "PARSED"
            }

        except Exception as e:
            logger.error(f"Failed parsing PDF file at {file_path}: {str(e)}", exc_info=True)
            raise e
