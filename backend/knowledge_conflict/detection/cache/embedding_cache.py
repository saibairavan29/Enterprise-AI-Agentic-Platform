import hashlib
import threading
import logging

logger = logging.getLogger('enterprise')

class EmbeddingCache:
    """
    Thread-safe, in-memory cache mapping text string SHA-256 hashes to generated embedding arrays.
    Prevents redundant, computationally expensive vector calculations.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(EmbeddingCache, cls).__new__(cls, *args, **kwargs)
                cls._instance._cache = {}
                cls._instance._hits = 0
                cls._instance._misses = 0
            return cls._instance

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get(self, text: str) -> list:
        if text is None:
            return None
            
        key = self._hash_text(text)
        with self._lock:
            val = self._cache.get(key)
            if val is not None:
                self._hits += 1
                return val
            self._misses += 1
            return None

    def set(self, text: str, embedding: list):
        if text is None or embedding is None:
            return
            
        key = self._hash_text(text)
        with self._lock:
            self._cache[key] = embedding

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "cache_hits": self._hits,
                "cache_misses": self._misses,
                "total_requests": self._hits + self._misses,
                "size": len(self._cache)
            }
