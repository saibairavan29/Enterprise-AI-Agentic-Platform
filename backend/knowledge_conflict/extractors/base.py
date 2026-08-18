from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """
    Abstract Base Class for text/property extractors.
    All concrete extractor strategies must implement the extract method.
    """
    @abstractmethod
    def extract(self, obj) -> list:
        """
        Extract list of text segment blocks or mapped keys from the given object.
        Returns a list of dictionaries with structure:
        [
            {
                "segment_id": str,
                "text": str,
                "page": int | None,
                "section": str | None,
                "metadata": dict
            }
        ]
        """
        pass
