from abc import ABC, abstractmethod
from edqi.explainability.logging.explainability_logger import ExplainabilityLogger

class BaseCache(ABC):
    """
    Polymorphic cache interface managing explainability report lookups.
    """
    @abstractmethod
    def get(self, key: str) -> dict:
        pass

    @abstractmethod
    def set(self, key: str, value: dict, timeout: int = 3600):
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def clear(self):
        pass


class MemoryCache(BaseCache):
    """
    In-memory local dictionary cache implementation.
    """
    def __init__(self):
        self._store = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> dict:
        key_str = str(key)
        if key_str in self._store:
            self.hits += 1
            ExplainabilityLogger.cache_hit(key_str)
            return self._store[key_str]
        
        self.misses += 1
        ExplainabilityLogger.cache_miss(key_str)
        return None

    def set(self, key: str, value: dict, timeout: int = 3600):
        key_str = str(key)
        self._store[key_str] = value
        ExplainabilityLogger.info(f"Cached explanation report for key: {key_str}")

    def delete(self, key: str):
        key_str = str(key)
        if key_str in self._store:
            del self._store[key_str]

    def clear(self):
        self._store.clear()
        self.hits = 0
        self.misses = 0
        ExplainabilityLogger.info("Explanation cache cleared.")
