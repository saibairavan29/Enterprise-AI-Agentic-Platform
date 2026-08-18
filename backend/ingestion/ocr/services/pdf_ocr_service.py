import logging
import fitz
import numpy as np
import cv2
import time
from django.utils import timezone
from .ocr_service import TesseractOCREngine
from ..utils.helpers import OCR_CONFIG

logger = logging.getLogger('enterprise')

class PDFOCRService:
    """
    Coordinates page-by-page text extraction for PDF files:
    - Prioritizes digital text extraction from PyMuPDF.
    - If a page has no text/below threshold, renders ONLY that page to an image buffer and runs OCR.
    - Merges the digital text and OCR text while preserving page sequence.
    """
    def execute(self, file_path):
        logger.info(f"PDF OCR extraction started. Target: {file_path}")
        start_time = time.perf_counter()
        
        engine = TesseractOCREngine()
        pages_processed = 0
        ocr_pages_count = 0
        full_text_list = []
        
        # Accumulate metrics
        confidences_list = []
        warnings = []
        errors = []

        try:
            with fitz.open(file_path) as doc:
                pages_processed = len(doc)
                
                for idx in range(pages_processed):
                    page = doc[idx]
                    
                    # 1. Try digital text extraction
                    digital_text = page.get_text().strip()
                    
                    # Check character count threshold
                    if len(digital_text) >= 20:
                        logger.debug(f"PDF Page {idx + 1}/{pages_processed}: Skip OCR (Digital text present)")
                        full_text_list.append(digital_text)
                    else:
                        logger.info(f"PDF Page {idx + 1}/{pages_processed}: Digital text empty/scanned. Running OCR.")
                        
                        # 2. Convert ONLY this single page to image in-memory
                        pix = page.get_pixmap(dpi=OCR_CONFIG["DPI"])
                        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        
                        # Convert to standard BGR for OpenCV
                        if pix.n == 4:
                            img = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2BGR)
                        else:
                            img = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
                            
                        # 3. Call OCR Engine
                        ocr_res = engine.extract_text(img)
                        full_text_list.append(ocr_res["text"])
                        
                        # Collect confidences
                        confidences_list.append(ocr_res["confidence"])
                        ocr_pages_count += 1
                        
                        if ocr_res["warnings"]:
                            warnings.extend(ocr_res["warnings"])
                            
        except Exception as e:
            logger.error(f"PDF OCR failed: {str(e)}", exc_info=True)
            from ..exceptions.ocr_exceptions import OCRExecutionException
            raise OCRExecutionException(f"PDF page-by-page OCR execution failed: {str(e)}")

        # 4. Resolve confidence metrics for the entire document run
        if confidences_list:
            avg_confs = [c["average"] for c in confidences_list]
            min_confs = [c["minimum"] for c in confidences_list]
            max_confs = [c["maximum"] for c in confidences_list]
            med_confs = [c["median"] for c in confidences_list]
            
            avg_val = sum(avg_confs) / len(avg_confs)
            min_val = min(min_confs)
            max_val = max(max_confs)
            med_val = sum(med_confs) / len(med_confs)
        else:
            # Entirely digital PDF (no page needed OCR)
            avg_val = 100.0
            min_val = 100.0
            max_val = 100.0
            med_val = 100.0

        elapsed_time = round(time.perf_counter() - start_time, 4)
        
        result = {
            "text": "\n\n".join(full_text_list),
            "confidence": {
                "average": round(avg_val, 2),
                "minimum": round(min_val, 2),
                "maximum": round(max_val, 2),
                "median": round(med_val, 2)
            },
            "language": OCR_CONFIG["LANGUAGE"],
            "processing_time": elapsed_time,
            "pages_processed": pages_processed,
            "engine": "Tesseract",
            "status": "OCR_COMPLETED",
            "ocr_status": "OCR_COMPLETED",
            "warnings": list(set(warnings)),
            "errors": errors,
            "execution_timestamp": timezone.now().isoformat()
        }
        
        logger.info(
            f"PDF_OCR_COMPLETE | Status: {result['status']} | "
            f"Pages Processed: {pages_processed} | "
            f"Pages OCRed: {ocr_pages_count} | "
            f"Avg Confidence: {avg_val}% | "
            f"Time: {elapsed_time}s"
        )
        
        return result
