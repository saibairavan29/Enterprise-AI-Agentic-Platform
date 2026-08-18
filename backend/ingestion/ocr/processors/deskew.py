import cv2
import numpy as np
import logging
from ..utils.helpers import OCR_CONFIG

logger = logging.getLogger('enterprise')

def determine_skew_angle(img):
    """
    Estimates the skew angle of the text region inside the image.
    """
    # Threshold to binary if not already binary
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    # Invert the image (Tesseract is dark text on light background)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Get all non-zero pixel coordinates
    pts = cv2.findNonZero(thresh)
    if pts is None:
        return 0.0
        
    # Calculate bounding box tilt angle
    rect = cv2.minAreaRect(pts)
    angle = rect[-1]
    
    # Standardize angle value
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = 90 - angle
        
    return angle

def rotate_image(img, angle):
    """
    Rotates the image matrix by the specified angle around its center.
    """
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    
    # Calculate rotation matrix
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Warp image boundary
    rotated = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def run_deskew(img):
    """
    Evaluates skew and rotates image if tilt exceeds angle configuration thresholds.
    """
    angle = determine_skew_angle(img)
    threshold = OCR_CONFIG["DESKEW_ANGLE_THRESHOLD"]
    
    if abs(angle) < threshold:
        # Skip deskewing for minor angles
        logger.debug(f"Deskew skipped. Angle: {angle:.2f} is below threshold: {threshold:.2f}")
        return img
        
    logger.info(f"Deskewing image. Angle detected: {angle:.2f} degrees")
    return rotate_image(img, angle)
