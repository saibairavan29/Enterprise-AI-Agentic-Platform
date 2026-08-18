from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """
    Abstract base class for all metadata extractors.
    Guarantees a common interface across all document segments.
    """
    @abstractmethod
    def extract(self, doc_obj, parser_output, ocr_output=None):
        """
        Extracts specific segment metadata.
        
        :param doc_obj: Ingested Document database model instance or dict.
        :param parser_output: Standard response dict returned by the document parser.
        :param ocr_output: Optional standard response dict returned by the OCR engine.
        :return: A dictionary representing the extracted metadata segment.
        """
        pass
