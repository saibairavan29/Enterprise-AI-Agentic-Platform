from abc import ABC, abstractmethod

class BaseOCREngine(ABC):
    """
    Abstract interface that all OCR Engine strategies (Tesseract, PaddleOCR, cloud-based engines)
    must implement. Ensures that replacing the underlying extraction tool does not affect
    parsers or other downstream pipelines.
    """
    @abstractmethod
    def extract_text(self, image_input, **kwargs):
        """
        Executes OCR extraction on the input image.
        
        :param image_input: File path string or a loaded numpy image array.
        :return: Standardized response contract dictionary.
        """
        pass
