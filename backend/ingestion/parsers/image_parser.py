from PIL import Image
import logging
from .base import BaseDocumentParser

logger = logging.getLogger('enterprise')

class ImageParser(BaseDocumentParser):
    """
    Concrete parser extracting structure metadata (resolution, color space format)
    from uploaded images using Pillow (PIL). Does not run OCR.
    """
    def parse(self, file_path):
        try:
            with Image.open(file_path) as img:
                # Load metadata
                width, height = img.size
                format_type = img.format
                mode = img.mode
                
                # Fetch resolution DPI details if defined
                dpi = img.info.get('dpi', (72, 72))
                
                return {
                    "content": "",  # Empty: OCR is executed in Milestone 4
                    "structured_data": {},
                    "metadata": {
                        "width": width,
                        "height": height,
                        "format": format_type,
                        "color_space": mode,
                        "dpi_horizontal": dpi[0],
                        "dpi_vertical": dpi[1]
                    },
                    "parser_type": "IMAGE",
                    "processing_status": "PARSED"
                }
                
        except Exception as e:
            logger.error(f"Failed parsing image file at {file_path}: {str(e)}", exc_info=True)
            raise e
