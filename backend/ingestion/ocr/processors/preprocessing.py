import cv2
import logging
from ..utils.helpers import OCR_CONFIG

logger = logging.getLogger('enterprise')

def convert_to_grayscale(img):
    """
    Converts image matrix to grayscale. Skips execution if already single-channel.
    """
    if len(img.shape) == 2 or img.shape[2] == 1:
        # Already Grayscale
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def run_denoise(img):
    """
    Applies Gaussian Blur for high-frequency noise removal.
    """
    return cv2.GaussianBlur(img, (3, 3), 0)
