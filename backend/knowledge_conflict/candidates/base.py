from abc import ABC, abstractmethod

class BasePairingStrategy(ABC):
    """
    Abstract Base Class representing a candidate pairing generation strategy.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.confidence = self.config.get("confidence", 50.0)

    @abstractmethod
    def generate_pairs(self, documents: list, records: list, segments: list) -> list:
        """
        Processes segments/documents/records and yields raw candidate pairing descriptions.
        Returns a list of candidate dictionaries:
        [
            {
                "source_document_id": str,
                "target_document_id": str,
                "source_segment_id": str,
                "target_segment_id": str,
                "source_text": str,
                "target_text": str,
                "source_page": int | None,
                "target_page": int | None,
                "source_section": str | None,
                "target_section": str | None,
                "strategy_used": str,
                "strategy_confidence": float,
                "entity_type": str,
                "metadata": dict
            }
        ]
        """
        pass
