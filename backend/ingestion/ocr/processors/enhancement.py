import cv2

def run_enhancement(img):
    """
    Applies Contrast Limited Adaptive Histogram Equalization (CLAHE) to balance lighting.
    """
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)
