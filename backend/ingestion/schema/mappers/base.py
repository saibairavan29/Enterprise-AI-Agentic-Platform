from abc import ABC, abstractmethod

class BaseMapper(ABC):
    """
    Abstract base class for all canonical schema mappers.
    """
    @abstractmethod
    def map_record(self, raw_record, resolver):
        """
        Maps a raw dictionary record into canonical and additional fields using the resolver.
        
        :param raw_record: A dictionary representing a single parsed record.
        :param resolver: FieldResolver instance to resolve raw keys.
        :return: A tuple of (mapped_canonical_fields, additional_fields, mapping_metadata)
        """
        pass
