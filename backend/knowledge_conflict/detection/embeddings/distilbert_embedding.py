from .sentence_transformer import SentenceTransformerEmbedding

class DistilBERTEmbedding(SentenceTransformerEmbedding):
    """
    DistilBERT Embedding strategy utilizing distilbert-base-nli-stsb-mean-tokens (768 dimensions).
    """
    def __init__(self, config: dict = None):
        config = config or {}
        # Enforce distilbert dimensions
        config.setdefault("model_name", "distilbert-base-nli-stsb-mean-tokens")
        config.setdefault("dimension", 768)
        super().__init__(config)
