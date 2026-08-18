from abc import ABC, abstractmethod

class BaseDocumentParser(ABC):
    """
    Abstract base interface that all document type parsers must implement.
    Ensures all parsers output a common object structure in Downstream Modules.
    """
    @abstractmethod
    def parse(self, file_path):
        """
        Parses the document at file_path and returns structured contents.
        
        :param file_path: Absolute filesystem path to the target document.
        :return: Standardized parsed dictionary or object.
        """
        pass
