import time
from .cosine_similarity import calculate_cosine_similarity
from ..cache.embedding_cache import EmbeddingCache
from ..exceptions.exceptions import SimilarityException

class SimilarityEngine:
    """
    Computes multiple similarity metrics (cosine similarity and relative length ratio)
    between two text components using cached embeddings.
    """
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.cache = EmbeddingCache()

    def compare_texts(self, text1: str, text2: str) -> dict:
        if not text1 or not text2:
            raise SimilarityException("Comparison text targets cannot be empty.")
            
        start_time = time.time()
        
        # 1. Resolve embedding for text1
        emb1 = self.cache.get(text1)
        cached1 = True
        if emb1 is None:
            cached1 = False
            emb1 = self.embedding_model.get_embedding(text1)
            self.cache.set(text1, emb1)
            
        # 2. Resolve embedding for text2
        emb2 = self.cache.get(text2)
        cached2 = True
        if emb2 is None:
            cached2 = False
            emb2 = self.embedding_model.get_embedding(text2)
            self.cache.set(text2, emb2)
            
        # 3. Calculate metrics
        cosine_sim = calculate_cosine_similarity(emb1, emb2)
        
        # Length similarity (ratio of shorter length to longer length)
        len1 = len(text1)
        len2 = len(text2)
        max_len = max(len1, len2)
        len_sim = min(len1, len2) / max_len if max_len > 0 else 1.0
        
        # Decide overall similarity (defaults to cosine_similarity)
        overall_sim = cosine_sim
        
        elapsed_duration = time.time() - start_time
        
        return {
            "overall_similarity": overall_sim,
            "similarity_metrics": {
                "cosine_similarity": round(cosine_sim, 4),
                "length_similarity": round(len_sim, 4),
                "overall_similarity": round(overall_sim, 4)
            },
            "model_used": self.embedding_model.__class__.__name__,
            "dimension": self.embedding_model.get_dimension(),
            "execution_time": round(elapsed_duration, 4),
            "cached": cached1 and cached2
        }
