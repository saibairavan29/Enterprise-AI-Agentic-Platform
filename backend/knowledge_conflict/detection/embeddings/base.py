from abc import ABC, abstractmethod

class BaseEmbeddingModel(ABC):
    """
    Abstract interface representing a text embedding model.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}

    @abstractmethod
    def get_embedding(self, text: str) -> list:
        """
        Generate a list of floats representing the embedding vector.
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Return the vector dimension size of the embedding.
        """
        pass
