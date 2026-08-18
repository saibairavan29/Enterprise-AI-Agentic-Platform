from abc import ABC, abstractmethod

class BaseTransformer(ABC):
    """
    Abstract base class for all field-level transformers.
    """
    @abstractmethod
    def transform(self, val, field_name, rules, changes_list):
        """
        Transforms the input value and logs changes if standardizations were applied.
        
        :param val: Incoming raw value.
        :param field_name: String path tracking the field location.
        :param rules: Loaded configuration rules dictionary.
        :param changes_list: List reference to record field change dictionaries.
        :return: Mapped standardized value.
        """
        pass
