import numpy as np
from ..exceptions.exceptions import SimilarityException

def calculate_cosine_similarity(v1: list, v2: list) -> float:
    """
    Computes cosine similarity between two numeric vector arrays.
    Returns float value between -1.0 and 1.0.
    """
    if not v1 or not v2:
        raise SimilarityException("Vectors cannot be empty.")
        
    try:
        arr1 = np.array(v1, dtype=float)
        arr2 = np.array(v2, dtype=float)
        
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
            
        dot_product = np.dot(arr1, arr2)
        sim = dot_product / (norm1 * norm2)
        
        # Clamp bounds
        return float(np.clip(sim, -1.0, 1.0))
    except Exception as e:
        raise SimilarityException(f"Failed to calculate cosine similarity: {str(e)}")
