import re
import unicodedata
from ..exceptions.exceptions import NormalizationException

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', "aren't", 
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', "can't", 
    'cannot', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 
    'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 
    'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 
    'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 
    'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 
    'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 
    'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'with', 
    'would', 'you', 'your', 'yours', 'yourself', 'yourselves'
}

class NormalizedText:
    """
    Data wrapper encapsulating both raw preserved text and normalized text copies.
    """
    def __init__(self, original: str, normalized: str, key_tokens: set = None):
        self.original = original
        self.normalized = normalized
        self.key_tokens = key_tokens or set()

    def __str__(self):
        return self.normalized


class TextNormalizer:
    """
    Normalizes text snippets to ensure consistent string comparisons across records.
    Filters out common stop words to retain key informative content tokens.
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
            
            # 4. Extract key tokens excluding filler stop words
            tokens = set(re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', lowercase_str))
            key_tokens = {t for t in tokens if t not in STOPWORDS}
            
            return NormalizedText(original=text, normalized=lowercase_str, key_tokens=key_tokens)
        except Exception as e:
            raise NormalizationException(f"Failed to normalize text: {str(e)}")

    @classmethod
    def extract_key_tokens(cls, text: str) -> set:
        """
        Extracts informative content words from raw/OCR text by removing filler stop words.
        """
        if not text:
            return set()
        clean = re.sub(r'\s+', ' ', str(text)).lower()
        tokens = set(re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', clean))
        return {t for t in tokens if t not in STOPWORDS}

