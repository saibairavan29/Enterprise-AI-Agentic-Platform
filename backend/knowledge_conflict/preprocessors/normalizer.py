import re
import unicodedata
from ..exceptions.exceptions import NormalizationException

class NormalizedText:
    """
    Data wrapper encapsulating both raw preserved text and normalized text copies.
    """
    def __init__(self, original: str, normalized: str):
        self.original = original
        self.normalized = normalized

    def __str__(self):
        return self.normalized


class TextNormalizer:
    """
    Normalizes text snippets to ensure consistent string comparisons across records.
    """
    def normalize(self, text: str) -> NormalizedText:
        if text is None:
            raise NormalizationException("Text input cannot be None.")
            
        try:
            # 1. Unicode Normalization (NFKC compatibility form)
            normalized_unic = unicodedata.normalize('NFKC', text)
            
            # 2. Clean spaces and newlines (replace multiple spacing with single space)
            clean_spaces = re.sub(r'\s+', ' ', normalized_unic).strip()
            
            # 3. Create lowercase copy for matching comparison
            lowercase_str = clean_spaces.lower()
            
            return NormalizedText(original=text, normalized=lowercase_str)
        except Exception as e:
            raise NormalizationException(f"Failed to normalize text: {str(e)}")
