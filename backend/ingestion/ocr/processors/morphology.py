import cv2
import numpy as np

def run_morphology(img):
    """
    Applies morphological open/close structures to clean up character borders.
    """
    # Use small kernel to avoid eroding thin font lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    return cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
