from django.test import TestCase
from ..similarity.cosine_similarity import calculate_cosine_similarity
from ..similarity.similarity_engine import SimilarityEngine
from ..embeddings.embedding_registry import EmbeddingModelRegistry
from ..exceptions.exceptions import SimilarityException

class SimilarityTests(TestCase):
    """
    Test suite validating cosine similarities mathematical computations
    and SimilarityEngine multi-metric outputs.
    """
    def test_cosine_similarity_edge_cases(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        
        # Identical vectors should yield 1.0 similarity
        self.assertAlmostEqual(calculate_cosine_similarity(v1, v2), 1.0, places=5)
        
        # Orthogonal vectors should yield 0.0 similarity
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(calculate_cosine_similarity(v1, v3), 0.0, places=5)
        
        # Negated vectors should yield -1.0 similarity
        v4 = [-1.0, 0.0, 0.0]
        self.assertAlmostEqual(calculate_cosine_similarity(v1, v4), -1.0, places=5)

    def test_cosine_similarity_raises_on_empty_list(self):
        with self.assertRaises(SimilarityException):
            calculate_cosine_similarity([], [1, 2])

    def test_similarity_engine_compare_texts(self):
        model = EmbeddingModelRegistry.get_model("MiniLMEmbedding")
        engine = SimilarityEngine(model)
        
        text1 = "Company policy says work starts at 9am."
        text2 = "Company policy states working hours begin at 9am."
        
        res = engine.compare_texts(text1, text2)
        
        # Verify result mappings
        self.assertIn("overall_similarity", res)
        self.assertIn("cosine_similarity", res["similarity_metrics"])
        self.assertIn("length_similarity", res["similarity_metrics"])
        self.assertEqual(res["model_used"], "MiniLMEmbedding")
        self.assertEqual(res["dimension"], 384)
        self.assertGreaterEqual(res["overall_similarity"], -1.0)
        self.assertLessEqual(res["overall_similarity"], 1.0)
