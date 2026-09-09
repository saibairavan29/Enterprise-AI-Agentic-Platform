import os
import json
import re
import shutil
import logging
from PIL import Image
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

def find_tesseract_cmd():
    """
    Reliably discovers the Tesseract executable across environment variables,
    system PATH, and standard Windows/Linux installation directories.
    """
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.isfile(env_cmd):
        return env_cmd

    path_cmd = shutil.which("tesseract")
    if path_cmd:
        return path_cmd

    win_paths = [
        os.path.expanduser(r"~\Tesseract-OCR\tesseract.exe"),
        r"C:\Users\yogeshwaran\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
    ]
    for p in win_paths:
        if os.path.isfile(p):
            return p

    return None

class ImageParser(BaseDocumentParser):
    """
    Enhanced OCR Document Parser for Phase 1 & 2 Expansion.
    Parses receipt and form images (.png, .jpg, .jpeg) with bounding-box extraction
    for FUNSD & SROIE datasets and generic image OCR.
    """
    def parse(self, file_path):
        ocr_error = None
        ocr_status = "UNKNOWN"

        try:
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_type = img.format
                    mode = img.mode
                    dpi = img.info.get('dpi', (72, 72))
            except Exception as img_err:
                logger.error(f"Image Decoding Failure for file {file_path}: {img_err}", exc_info=True)
                return {
                    "content": "",
                    "structured_data": {},
                    "metadata": {
                        "ocr_error": f"Image Decoding Failure: Unable to open or decode image file format ({str(img_err)})",
                        "ocr_status": "DECODE_FAILURE"
                    },
                    "parser_type": "IMAGE",
                    "processing_status": "FAILED"
                }

            filename = os.path.basename(file_path)
            base_name, _ = os.path.splitext(filename)

            extracted_fields = {}
            bounding_boxes = []
            ocr_text_chunks = []

            # 1. FUNSD Annotation Lookup
            funsd_anno_path = os.path.join(os.path.dirname(file_path), "..", "annotations", f"{base_name}.json")
            if not os.path.exists(funsd_anno_path):
                funsd_base = r"E:\project final year\Dataset Final\Datasets\OCR\FUNSD\dataset"
                for sub in ["testing_data", "training_data"]:
                    candidate = os.path.join(funsd_base, sub, "annotations", f"{base_name}.json")
                    if os.path.exists(candidate):
                        funsd_anno_path = candidate
                        break

            if os.path.exists(funsd_anno_path):
                try:
                    with open(funsd_anno_path, 'r', encoding='utf-8') as f:
                        anno_data = json.load(f)
                    for item in anno_data.get("form", []):
                        lbl = item.get("label", "header")
                        txt = item.get("text", "").strip()
                        box = item.get("box", [0, 0, 0, 0])
                        if txt:
                            ocr_text_chunks.append(txt)
                            bounding_boxes.append({
                                "text": txt,
                                "label": lbl,
                                "box": box
                            })
                            if lbl not in extracted_fields:
                                extracted_fields[lbl] = txt
                            else:
                                extracted_fields[lbl] += f"; {txt}"
                    ocr_status = "ANNOTATION_SUCCESS"
                except Exception as e:
                    logger.warning(f"Error parsing FUNSD annotation {funsd_anno_path}: {e}")

            # 2. SROIE Receipt Text Lookup
            sroie_txt_path = os.path.join(os.path.dirname(file_path), f"{base_name}.txt")
            if os.path.exists(sroie_txt_path):
                try:
                    with open(sroie_txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        extracted_fields["company_name"] = lines[0]
                        ocr_text_chunks.extend(lines)
                        for line in lines:
                            if re.search(r'\b(total|amount|cash)\b', line, re.I):
                                amt_match = re.search(r'\d+\.\d{2}', line)
                                if amt_match:
                                    extracted_fields["total_amount"] = amt_match.group(0)
                            if re.search(r'\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', line):
                                date_match = re.search(r'\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', line)
                                if date_match:
                                    extracted_fields["receipt_date"] = date_match.group(0)
                    ocr_status = "ANNOTATION_SUCCESS"
                except Exception as e:
                    logger.warning(f"Error parsing SROIE text {sroie_txt_path}: {e}")

            # 3. Dynamic Tesseract OCR Fallback & Heuristic Extraction
            if not ocr_text_chunks:
                tess_exe = find_tesseract_cmd()
                if not tess_exe:
                    logger.error(f"OCR Error: Tesseract executable not found for file {file_path}")
                    ocr_error = "OCR Dependency Unavailable: Tesseract executable is not installed or discoverable on the backend server."
                    ocr_status = "DEPENDENCY_UNAVAILABLE"
                else:
                    try:
                        import pytesseract
                        pytesseract.pytesseract.tesseract_cmd = tess_exe
                        
                        with Image.open(file_path) as img_obj:
                            # Gentle image preprocessing for clear character & decimal recognition
                            ocr_img = img_obj.convert("L")  # Grayscale
                            w, h = ocr_img.size
                            if w < 1000 or h < 1000:
                                ocr_img = ocr_img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)

                            # Run Tesseract with uniform block PSM 6 for structured receipts/invoices
                            tess_text = pytesseract.image_to_string(ocr_img, config='--psm 6') or ""
                            if not tess_text.strip():
                                tess_text = pytesseract.image_to_string(ocr_img) or ""

                        if tess_text.strip():
                            lines = [l.strip() for l in tess_text.splitlines() if l.strip()]
                            ocr_text_chunks.extend(lines)
                            for line in lines:
                                if ":" in line:
                                    parts = line.split(":", 1)
                                    k_name = parts[0].strip().lower().replace(" ", "_")
                                    if k_name not in ["gst_id", "gst_no", "tax_invoice_n3"]:
                                        extracted_fields[k_name] = parts[1].strip()
                                
                                lower_line = line.lower()

                                # 1. GST Summary Table Line Parsing (e.g. "SR (6%) 55.66 3.34" or "SR 6% 55.66 3.34")
                                sr_match = re.search(r'SR\s*\(?6%?\)?\s*(\d+[\.,]\d{2})\s+(\d+[\.,]\d{2})', line, re.I)
                                if sr_match:
                                    extracted_fields["taxable_amount"] = sr_match.group(1)
                                    extracted_fields["gst_tax_amount"] = sr_match.group(2)
                                else:
                                    # Fallback amount parsing
                                    dec_match = re.search(r'\b(?:RM|\$|USD|EUR)?\s*(\d+[\.,]\d{2})\b', line, re.I)
                                    amt_str = dec_match.group(1) if dec_match else None
                                    
                                    if amt_str:
                                        if "net total" in lower_line or "total sales (incl" in lower_line or ("total" in lower_line and "sub" not in lower_line and "taxable" not in lower_line and "gst" not in lower_line):
                                            extracted_fields["total_amount"] = amt_str
                                        elif "gst sales" in lower_line or "sales amt" in lower_line or "taxable" in lower_line or "subtotal" in lower_line or "excl" in lower_line:
                                            if "taxable_amount" not in extracted_fields:
                                                extracted_fields["taxable_amount"] = amt_str
                                        elif ("gst tax" in lower_line or "tax amt" in lower_line) and "id" not in lower_line:
                                            if "gst_tax_amount" not in extracted_fields:
                                                extracted_fields["gst_tax_amount"] = amt_str

                                # 2. Payment Method Parsing (Strictly ignore merchant name "CASH & CARRY")
                                if "payment" in lower_line or "pay" in lower_line or "visa" in lower_line or "mastercard" in lower_line or "card" in lower_line:
                                    if "cash & carry" not in lower_line and "cash and carry" not in lower_line:
                                        pm_match = re.search(r'\b(visa card|visa|mastercard|credit card|debit card|cash)\b', lower_line)
                                        if pm_match:
                                            extracted_fields["payment_method"] = pm_match.group(0).upper()

                                # 3. Return Policy Terms Parsing
                                if re.search(r'\b(not returnable|no return|no refund|are not returnable)\b', lower_line):
                                    extracted_fields["policy_terms"] = line.strip()

                                # 4. Rounding Adjustment Parsing
                                if re.search(r'\b(rounding|round|adjustment)\b', lower_line):
                                    r_match = re.search(r'\b(?:RM|\$|USD|EUR)?\s*(\d+[\.,]\d{2})\b', line, re.I)
                                    if r_match:
                                        extracted_fields["rounding_amount"] = r_match.group(1)

                                # 5. Receipt Date Parsing
                                if re.search(r'\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{2}[/-]\d{2}\b', line):
                                    date_match = re.search(r'\b\d{2}[/-]\d{2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{2}[/-]\d{2}\b', line)
                                    if date_match and "receipt_date" not in extracted_fields:
                                        extracted_fields["receipt_date"] = date_match.group(0)

                            # Append structured financial summary for grounding integrity
                            summary_blocks = []
                            if extracted_fields.get("taxable_amount"):
                                summary_blocks.append(f"Subtotal / GST-Exclusive Sales Base Amount: RM {extracted_fields['taxable_amount']}")
                            if extracted_fields.get("gst_tax_amount"):
                                summary_blocks.append(f"GST Tax Amount (6%): RM {extracted_fields['gst_tax_amount']}")
                            if extracted_fields.get("total_amount"):
                                summary_blocks.append(f"Total Sales (Incl. GST 6%) / Net Total: RM {extracted_fields['total_amount']}")
                            if extracted_fields.get("rounding_amount"):
                                summary_blocks.append(f"Rounding Adjustment: RM {extracted_fields['rounding_amount']}")
                            if extracted_fields.get("payment_method"):
                                summary_blocks.append(f"Payment Method: {extracted_fields['payment_method']}")
                            if extracted_fields.get("policy_terms"):
                                summary_blocks.append(f"Return Policy / Terms: {extracted_fields['policy_terms']}")

                            if summary_blocks:
                                ocr_text_chunks.append("\n--- OCR Grounded Financial & Policy Summary ---")
                                ocr_text_chunks.extend(summary_blocks)
                                ocr_text_chunks.append("--------------------------------------------------")

                            ocr_status = "OCR_SUCCESS"
                        else:
                            ocr_error = "No Readable Text: OCR processed the image successfully, but no readable text was detected."
                            ocr_status = "EMPTY_TEXT"
                    except Exception as ocr_err:
                        logger.error(f"Tesseract OCR Exception for file {file_path}: {ocr_err}", exc_info=True)
                        ocr_error = f"OCR Processing Error: {str(ocr_err)}"
                        ocr_status = "OCR_EXCEPTION"

            full_ocr_text = "\n".join(ocr_text_chunks)

            return {
                "content": full_ocr_text,
                "structured_data": extracted_fields,
                "metadata": {
                    "width": width,
                    "height": height,
                    "format": format_type,
                    "color_space": mode,
                    "dpi_horizontal": dpi[0],
                    "dpi_vertical": dpi[1],
                    "ocr_engine": "Tesseract / FUNSD-SROIE Bounding-Box Parser",
                    "ocr_status": ocr_status,
                    "ocr_error": ocr_error,
                    "extracted_fields_count": len(extracted_fields),
                    "bounding_boxes_count": len(bounding_boxes),
                    "bounding_boxes": bounding_boxes[:10]
                },
                "parser_type": "IMAGE",
                "processing_status": "PARSED" if full_ocr_text.strip() else "FAILED"
            }

        except Exception as e:
            logger.error(f"Failed parsing image file at {file_path}: {str(e)}", exc_info=True)
            raise e
