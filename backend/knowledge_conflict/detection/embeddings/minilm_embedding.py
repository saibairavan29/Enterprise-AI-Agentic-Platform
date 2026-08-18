from .sentence_transformer import SentenceTransformerEmbedding

class MiniLMEmbedding(SentenceTransformerEmbedding):
    """
    MiniLM Embedding strategy utilizing all-MiniLM-L6-v2 (384 dimensions).
    """
    def __init__(self, config: dict = None):
        config = config or {}
        # Enforce all-MiniLM-L6-v2 dimensions
        config.setdefault("model_name", "all-MiniLM-L6-v2")
        config.setdefault("dimension", 384)
        super().__init__(config)
