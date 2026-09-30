import hashlib
import logging
from .base import BaseEmbeddingModel
from ..exceptions.exceptions import EmbeddingException

logger = logging.getLogger('enterprise')

class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """
    SentenceTransformer embedding wrapper.
    Attempts to use the 'sentence-transformers' package, falling back
    to a deterministic normalized frequency vector if offline or models are missing.
    """
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.model_name = self.config.get("model_name", "all-MiniLM-L6-v2")
        self.dimension = self.config.get("dimension", 384)
        self.model = None
        
        # Staged load
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded SentenceTransformer model: {self.model_name}")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer could not load '{self.model_name}' ({str(e)}). "
                "Active offline fallback will generate deterministic vectors."
            )

    def get_embedding(self, text: str) -> list:
        if not text:
            raise EmbeddingException("Text input cannot be empty.")
            
        try:
            if self.model is not None:
                # Generate using HuggingFace sentence transformer directly via PyTorch tensor to bypass NumPy C-API mismatches
                vec = self.model.encode(text, convert_to_numpy=False)
                if hasattr(vec, 'tolist'):
                    return vec.tolist()
                return list(vec)
            else:
                return self._generate_fallback(text)
        except Exception as e:
            logger.warning(f"SentenceTransformer encode failed ({str(e)}). Using deterministic fallback.")
            return self._generate_fallback(text)

    def get_dimension(self) -> int:
        return self.dimension

    def _generate_fallback(self, text: str) -> list:
        """
        Generates a deterministic unit-length vector derived from the input text's SHA-256 checksum.
        Ensures unit testing consistency without external web calls.
        """
        try:
            import numpy as np
            h = hashlib.sha256(text.encode('utf-8')).digest()
            seed = int.from_bytes(h[:4], byteorder='big')
            
            rng = np.random.default_rng(seed)
            vec = rng.normal(size=self.dimension)
            
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
                
            return vec.tolist()
        except Exception:
            import math
            h = hashlib.sha256(text.encode('utf-8')).digest()
            vec = []
            for i in range(self.dimension):
                val = math.sin((h[i % len(h)] + i) * 1.5)
                vec.append(val)
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            return vec
