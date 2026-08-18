import logging
from ..exceptions.exceptions import EmbeddingException

logger = logging.getLogger('enterprise')

class EmbeddingModelRegistry:
    """
    Registry for managing pluggable text embedding model classes.
    """
    _registry = {}

    @classmethod
    def register(cls, name: str, model_class):
        cls._registry[name] = model_class
        logger.info(f"Registered embedding model: {name}")

    @classmethod
    def get_model(cls, name: str, config: dict = None):
        """
        Resolves and instantiates the registered embedding class strategy.
        """
        if name not in cls._registry:
            raise EmbeddingException(f"Embedding model '{name}' is not registered in EmbeddingModelRegistry.")
        model_class = cls._registry[name]
        return model_class(config)

# Register the models
from .sentence_transformer import SentenceTransformerEmbedding
from .minilm_embedding import MiniLMEmbedding
from .distilbert_embedding import DistilBERTEmbedding

EmbeddingModelRegistry.register("SentenceTransformerEmbedding", SentenceTransformerEmbedding)
EmbeddingModelRegistry.register("MiniLMEmbedding", MiniLMEmbedding)
EmbeddingModelRegistry.register("DistilBERTEmbedding", DistilBERTEmbedding)
