from django.test import TestCase
from ..preprocessors.normalizer import TextNormalizer
from ..preprocessors.segmenter import RegexSegmenter
from ..exceptions.exceptions import NormalizationException, SegmentationException

class PreprocessingTests(TestCase):
    """
    Test suite validating text normalizer operations and rules-based segmentation structures.
    """
    def test_text_normalizer_spacing_and_casing(self):
        normalizer = TextNormalizer()
        input_txt = "   This is  \n a text \t with NFKC unicode \u2122.   "
        
        result = normalizer.normalize(input_txt)
        # Should trim and map multiple white spaces to a single space
        self.assertEqual(result.original, input_txt)
        self.assertEqual(result.normalized, "this is a text with nfkc unicode tm.")
        
    def test_text_normalizer_raises_on_none(self):
        normalizer = TextNormalizer()
        with self.assertRaises(NormalizationException):
            normalizer.normalize(None)

    def test_regex_segmenter_splits(self):
        segmenter = RegexSegmenter()
        markdown_text = (
            "# Document Policy Heading\n\n"
            "Paragraph one sentence one. Paragraph one sentence two e.g. details.\n\n"
            "## Sub Section Title\n\n"
            "Paragraph two content text. Second sentence details here!"
        )
        
        segments = segmenter.segment(markdown_text, source_id="doc1")
        
        # Verify paragraph counts
        paragraphs = [s for s in segments if s["type"] == "paragraph"]
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0]["section"], "Document Policy Heading")
        self.assertEqual(paragraphs[1]["section"], "Sub Section Title")
        
        # Verify sentence counts
        sentences = [s for s in segments if s["type"] == "sentence"]
        # Sentence end checking splits correctly and preserves periods
        self.assertEqual(len(sentences), 4)
        self.assertEqual(sentences[0]["text"], "Paragraph one sentence one.")
        self.assertEqual(sentences[1]["text"], "Paragraph one sentence two e.g. details.")
        
        # Verify section header registration
        sections = [s for s in segments if s["type"] == "section"]
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["text"], "# Document Policy Heading")
        
    def test_regex_segmenter_raises_on_none(self):
        segmenter = RegexSegmenter()
        with self.assertRaises(SegmentationException):
            segmenter.segment(None)
