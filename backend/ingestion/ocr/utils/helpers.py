import os
from django.core.exceptions import ValidationError

# Cache configuration variables once on application loading to avoid repeated system environment IO checks.
OCR_CONFIG = {
    "LANGUAGE": os.getenv("OCR_LANGUAGE", "eng"),
    "DPI": int(os.getenv("OCR_DPI", "300")),
    "TIMEOUT": int(os.getenv("OCR_TIMEOUT", "30")),
    "ENGINE": os.getenv("OCR_ENGINE", "Tesseract"),
    "PAGE_SEGMENTATION_MODE": int(os.getenv("OCR_PAGE_SEGMENTATION_MODE", "3")),
    "ENGINE_MODE": int(os.getenv("OCR_ENGINE_MODE", "3")),
    "CONFIDENCE_THRESHOLD": float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "50.0")),
    "ENABLE_GRAYSCALE": os.getenv("OCR_ENABLE_GRAYSCALE", "True").lower() == "true",
    "ENABLE_DENOISE": os.getenv("OCR_ENABLE_DENOISE", "True").lower() == "true",
    "ENABLE_DESKEW": os.getenv("OCR_ENABLE_DESKEW", "True").lower() == "true",
    "ENABLE_CLAHE": os.getenv("OCR_ENABLE_CLAHE", "True").lower() == "true",
    "ENABLE_THRESHOLDING": os.getenv("OCR_ENABLE_THRESHOLDING", "True").lower() == "true",
    "ENABLE_MORPHOLOGY": os.getenv("OCR_ENABLE_MORPHOLOGY", "True").lower() == "true",
    
    # Preprocessing thresholds
    "DESKEW_ANGLE_THRESHOLD": float(os.getenv("OCR_DESKEW_ANGLE_THRESHOLD", "0.5")),
    "TESSERACT_CMD": os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
}

def validate_config():
    """
    Validates loaded settings configurations and throws OCRConfigurationException.
    """
    from ..exceptions.ocr_exceptions import OCRConfigurationException
    
    if OCR_CONFIG["DPI"] <= 0:
        raise OCRConfigurationException("OCR_DPI must be a positive integer.")
    if OCR_CONFIG["TIMEOUT"] < 0:
        raise OCRConfigurationException("OCR_TIMEOUT must be a non-negative integer.")
    if OCR_CONFIG["CONFIDENCE_THRESHOLD"] < 0.0 or OCR_CONFIG["CONFIDENCE_THRESHOLD"] > 100.0:
        raise OCRConfigurationException("OCR_CONFIDENCE_THRESHOLD must be between 0.0 and 100.0.")
