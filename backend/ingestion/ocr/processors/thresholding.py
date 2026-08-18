import cv2

def run_threshold(img):
    """
    Applies adaptive Otsu binarization to binarize grayscale images.
    """
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Apply Otsu's thresholding
    return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
