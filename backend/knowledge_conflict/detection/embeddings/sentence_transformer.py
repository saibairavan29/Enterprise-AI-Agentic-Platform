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
                # Generate using HuggingFace sentence transformer
                vec = self.model.encode(text)
                return vec.tolist()
            else:
                return self._generate_fallback(text)
        except Exception as e:
            raise EmbeddingException(f"Failed to generate embedding: {str(e)}")

    def get_dimension(self) -> int:
        return self.dimension

    def _generate_fallback(self, text: str) -> list:
        """
        Generates a deterministic unit-length vector derived from the input text's SHA-256 checksum.
        Ensures unit testing consistency without external web calls.
        """
        import numpy as np
        h = hashlib.sha256(text.encode('utf-8')).digest()
        seed = int.from_bytes(h[:4], byteorder='big')
        
        rng = np.random.default_rng(seed)
        vec = rng.normal(size=self.dimension)
        
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        return vec.tolist()
