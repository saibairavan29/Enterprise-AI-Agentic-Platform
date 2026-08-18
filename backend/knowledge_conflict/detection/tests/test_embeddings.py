from django.test import TestCase
from ..embeddings.embedding_registry import EmbeddingModelRegistry
from ..cache.embedding_cache import EmbeddingCache

class EmbeddingsTests(TestCase):
    """
    Unit tests validating pluggable embedding strategy loading, caches,
    dimensions, and deterministic fallback calculations.
    """
    def setUp(self):
        self.cache = EmbeddingCache()
        self.cache.clear()

    def test_embedding_model_registry_resolution(self):
        # Resolve and instantiate MiniLM
        model = EmbeddingModelRegistry.get_model("MiniLMEmbedding")
        self.assertEqual(model.get_dimension(), 384)
        
        # Resolve and instantiate DistilBERT
        model_db = EmbeddingModelRegistry.get_model("DistilBERTEmbedding")
        self.assertEqual(model_db.get_dimension(), 768)

    def test_embedding_cache_lookups(self):
        text = "Semantic operational rules text."
        
        # First query should be a cache miss
        emb = self.cache.get(text)
        self.assertIsNone(emb)
        self.assertEqual(self.cache.stats["cache_misses"], 1)
        self.assertEqual(self.cache.stats["cache_hits"], 0)
        
        # Populate cache
        mock_embedding = [0.1, 0.2, 0.3]
        self.cache.set(text, mock_embedding)
        
        # Second query should be a cache hit
        emb_hit = self.cache.get(text)
        self.assertEqual(emb_hit, mock_embedding)
        self.assertEqual(self.cache.stats["cache_hits"], 1)
        self.assertEqual(self.cache.stats["cache_misses"], 1)

    def test_fallback_generates_normalized_vectors(self):
        model = EmbeddingModelRegistry.get_model("MiniLMEmbedding")
        vec = model.get_embedding("Deterministic text snippet.")
        
        # Assert dimensions
        self.assertEqual(len(vec), 384)
        
        # Assert unit-length normalization (norm should be very close to 1.0)
        import numpy as np
        norm = np.linalg.norm(np.array(vec))
        self.assertAlmostEqual(norm, 1.0, places=5)
