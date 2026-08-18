class OCRException(Exception):
    """
    Base exception class for all OCR-related errors.
    """
    pass

class OCRExecutionException(OCRException):
    """
    Raised when the OCR engine fails to execute text extraction.
    """
    pass

class OCRTimeoutException(OCRException):
    """
    Raised when the OCR engine execution exceeds the configured time threshold.
    """
    pass

class OCRConfigurationException(OCRException):
    """
    Raised when OCR parameters or configuration metrics are invalid or missing.
    """
    pass

class OCRImageReadException(OCRException):
    """
    Raised when the image processor fails to read or load the file stream.
    """
    pass

class OCRUnsupportedFormatException(OCRException):
    """
    Raised when the input file format (extension or MIME) is not supported.
    """
    pass

class TesseractNotInstalledException(OCRException):
    """
    Raised when the Tesseract OCR binary cannot be resolved on the active machine.
    """
    pass

class OCRConfidenceException(OCRException):
    """
    Raised when confidence scoring constraints are violated.
    """
    pass
