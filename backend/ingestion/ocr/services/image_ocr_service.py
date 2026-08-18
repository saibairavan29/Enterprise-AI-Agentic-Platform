import logging
from .ocr_service import TesseractOCREngine
from ..utils.helpers import OCR_CONFIG

logger = logging.getLogger('enterprise')

class ImageOCRService:
    """
    Service coordinating OCR text extraction for standalone image files (PNG, JPEG, TIFF, BMP).
    It references only the abstract engine interface / resolved implementation strategy.
    """
    def execute(self, image_path):
        """
        Executes OCR on an image file and returns the standardized contract.
        
        :param image_path: Path to the target image file.
        :return: Standardized response contract dictionary.
        """
        logger.info(f"Image OCR request started. Target: {image_path}")
        
        # Instantiate active engine (Can be dynamic / factory-based in future)
        engine = TesseractOCREngine()
        
        result = engine.extract_text(image_path)
        return result
