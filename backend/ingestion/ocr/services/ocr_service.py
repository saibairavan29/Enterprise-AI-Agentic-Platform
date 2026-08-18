import cv2
import logging
import pytesseract
from pytesseract.pytesseract import TesseractNotFoundError
import numpy as np
from django.utils import timezone

from .base import BaseOCREngine
from ..exceptions.ocr_exceptions import (
    OCRExecutionException,
    OCRTimeoutException,
    OCRConfigurationException,
    OCRImageReadException,
    OCRUnsupportedFormatException,
    TesseractNotInstalledException,
    OCRConfidenceException
)
from ..processors import (
    convert_to_grayscale,
    run_denoise,
    run_deskew,
    run_threshold,
    run_enhancement,
    run_morphology
)
from ..utils.helpers import OCR_CONFIG, validate_config
from ..utils.confidence import analyze_confidence
from ..utils.timer import measure_time

# Configure local package logging
logger = logging.getLogger('enterprise')

# Set Tesseract binary path if configured
if OCR_CONFIG["TESSERACT_CMD"]:
    pytesseract.pytesseract.tesseract_cmd = OCR_CONFIG["TESSERACT_CMD"]

class TesseractOCREngine(BaseOCREngine):
    """
    Tesseract implementation of the BaseOCREngine strategy.
    It isolates pytesseract references and coordinates the OpenCV preprocessing steps.
    """
    def extract_text(self, image_input, **kwargs):
        # 1. Validate configurations
        try:
            validate_config()
        except Exception as ce:
            logger.error(f"OCR Configuration Error: {str(ce)}")
            raise OCRConfigurationException(str(ce))

        # 2. Image Loading
        img = None
        if isinstance(image_input, str):
            try:
                img = cv2.imread(image_input)
                if img is None:
                    raise OCRImageReadException(f"Failed to read image from path: {image_input}")
            except Exception as e:
                logger.error(f"Image load exception for path {image_input}: {str(e)}")
                if isinstance(e, OCRImageReadException):
                    raise e
                raise OCRImageReadException(f"Could not load image: {str(e)}")
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise OCRUnsupportedFormatException("Unsupported image input type. Must be a file path string or numpy array.")

        # 3. OpenCV Preprocessing Pipeline (Configurable and optional)
        warnings = []
        errors = []
        processed_img = img.copy()

        with measure_time() as timer:
            try:
                # Grayscale conversion
                if OCR_CONFIG["ENABLE_GRAYSCALE"]:
                    processed_img = convert_to_grayscale(processed_img)

                # Denoise
                if OCR_CONFIG["ENABLE_DENOISE"]:
                    processed_img = run_denoise(processed_img)

                # Deskew
                if OCR_CONFIG["ENABLE_DESKEW"]:
                    processed_img = run_deskew(processed_img)

                # Contrast Enhancement (CLAHE)
                if OCR_CONFIG["ENABLE_CLAHE"]:
                    processed_img = run_enhancement(processed_img)

                # Binarization
                if OCR_CONFIG["ENABLE_THRESHOLDING"]:
                    processed_img = run_threshold(processed_img)

                # Morphological opening
                if OCR_CONFIG["ENABLE_MORPHOLOGY"]:
                    processed_img = run_morphology(processed_img)

            except Exception as pe:
                logger.warning(f"OCR Preprocessing warning occurred: {str(pe)}")
                warnings.append(f"Preprocessing warning: {str(pe)}")

            # 4. Tesseract OCR execution under timeout scope
            tess_config = f"--oem {OCR_CONFIG['ENGINE_MODE']} --psm {OCR_CONFIG['PAGE_SEGMENTATION_MODE']}"
            
            try:
                # Call Tesseract for raw text and TSV confidence structures
                extracted_text = pytesseract.image_to_string(
                    processed_img,
                    lang=OCR_CONFIG["LANGUAGE"],
                    config=tess_config,
                    timeout=OCR_CONFIG["TIMEOUT"]
                )
                
                tsv_data = pytesseract.image_to_data(
                    processed_img,
                    lang=OCR_CONFIG["LANGUAGE"],
                    config=tess_config,
                    timeout=OCR_CONFIG["TIMEOUT"]
                )
                
            except TesseractNotFoundError:
                logger.error("Tesseract OCR binary is missing or not installed.")
                raise TesseractNotInstalledException("Tesseract OCR execution failed because the binary is not installed.")
            except RuntimeError as re:
                if "timeout" in str(re).lower():
                    logger.error(f"OCR execution timed out after {OCR_CONFIG['TIMEOUT']} seconds.")
                    raise OCRTimeoutException(f"OCR processing timed out: {str(re)}")
                logger.error(f"OCR Engine runtime error: {str(re)}")
                raise OCRExecutionException(f"Tesseract engine run failed: {str(re)}")
            except Exception as ex:
                logger.error(f"Unhandled Tesseract exception occurred: {str(ex)}")
                raise OCRExecutionException(f"Third-party OCR library exception: {str(ex)}")

        # 5. Confidence Analysis
        try:
            conf_metrics = analyze_confidence(tsv_data)
        except Exception as conf_err:
            logger.error(f"Confidence calculation failure: {str(conf_err)}")
            raise OCRConfidenceException(f"Failed to calculate OCR confidence: {str(conf_err)}")

        # Validate against confidence thresholds
        avg_conf = conf_metrics["average"]
        if avg_conf < OCR_CONFIG["CONFIDENCE_THRESHOLD"] and conf_metrics["word_count"] > 0:
            msg = f"Average OCR confidence {avg_conf}% is below configured threshold of {OCR_CONFIG['CONFIDENCE_THRESHOLD']}%"
            logger.warning(msg)
            warnings.append(msg)

        processing_time = timer["elapsed"]

        result = {
            "text": extracted_text.strip(),
            "confidence": {
                "average": avg_conf,
                "minimum": conf_metrics["minimum"],
                "maximum": conf_metrics["maximum"],
                "median": conf_metrics["median"]
            },
            "language": OCR_CONFIG["LANGUAGE"],
            "processing_time": processing_time,
            "pages_processed": 1,
            "engine": "Tesseract",
            "status": "OCR_COMPLETED",
            "ocr_status": "OCR_COMPLETED",
            "warnings": warnings,
            "errors": errors,
            "execution_timestamp": timezone.now().isoformat()
        }

        # 7. Audit Log Execution Trace (Does NOT write document contents)
        logger.info(
            f"OCR_EXECUTION | Status: {result['status']} | "
            f"Engine: {result['engine']} | "
            f"Pages: {result['pages_processed']} | "
            f"Avg Confidence: {avg_conf}% | "
            f"Time: {processing_time}s"
        )

        return result
