import time
from .cosine_similarity import calculate_cosine_similarity
from ..cache.embedding_cache import EmbeddingCache
from ..exceptions.exceptions import SimilarityException

from ...preprocessors.normalizer import TextNormalizer

class SimilarityEngine:
    """
    Computes multiple similarity metrics (cosine similarity and relative length ratio)
    between two text components using cached embeddings and fast lexical pre-filtering.
    """
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.cache = EmbeddingCache()
        self.normalizer = TextNormalizer()

    def compare_texts(self, text1: str, text2: str) -> dict:
        if not text1 or not text2:
            raise SimilarityException("Comparison text targets cannot be empty.")
            
        start_time = time.time()
        
        # 1. Fast Lexical Key-Token Jaccard check
        toks1 = set(self.normalizer.extract_key_tokens(text1))
        toks2 = set(self.normalizer.extract_key_tokens(text2))
        
        intersection_count = len(toks1.intersection(toks2))
        union_count = len(toks1.union(toks2))
        token_sim = (intersection_count / union_count) if union_count > 0 else 0.0

        # Fast pre-filtering: if both texts are substantial (>30 chars) and share 0 key tokens,
        # skip neural embedding inference completely for 10x-20x speedup.
        if intersection_count == 0 and len(text1) > 30 and len(text2) > 30:
            cosine_sim = 0.0
            cached1, cached2 = True, True
        else:
            # Resolve embeddings for text1 & text2
            emb1 = self.cache.get(text1)
            cached1 = emb1 is not None
            if emb1 is None:
                emb1 = self.embedding_model.get_embedding(text1)
                self.cache.set(text1, emb1)
                
            emb2 = self.cache.get(text2)
            cached2 = emb2 is not None
            if emb2 is None:
                emb2 = self.embedding_model.get_embedding(text2)
                self.cache.set(text2, emb2)
                
            cosine_sim = calculate_cosine_similarity(emb1, emb2)

        # Length similarity (ratio of shorter length to longer length)
        len1 = len(text1)
        len2 = len(text2)
        max_len = max(len1, len2)
        len_sim = min(len1, len2) / max_len if max_len > 0 else 1.0
        
        # Hybrid overall similarity blender (0.6 Neural + 0.4 Lexical)
        overall_sim = round((0.60 * cosine_sim) + (0.40 * token_sim), 4)
        
        elapsed_duration = time.time() - start_time
        
        return {
            "overall_similarity": overall_sim,
            "similarity_metrics": {
                "cosine_similarity": round(cosine_sim, 4),
                "token_similarity": round(token_sim, 4),
                "length_similarity": round(len_sim, 4),
                "overall_similarity": round(overall_sim, 4)
            },
            "model_used": self.embedding_model.__class__.__name__,
            "dimension": self.embedding_model.get_dimension(),
            "execution_time": round(elapsed_duration, 4),
            "cached": cached1 and cached2
        }
