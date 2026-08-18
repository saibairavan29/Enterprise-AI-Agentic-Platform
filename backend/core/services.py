import logging
from django.db import transaction

class BaseService:
    """
    Base service class defining core utilities for logging and transactional operations.
    All downstream service logic (ingestion, parsing, ML pipeline calls) should inherit from this class.
    """
    def __init__(self):
        self.logger = logging.getLogger(f"enterprise.services.{self.__class__.__name__}")

    def execute(self, *args, **kwargs):
        """
        Execute wrapper that handles transaction atomicity and logging.
        """
        self.logger.info(f"Starting execution of service: {self.__class__.__name__}")
        try:
            with transaction.atomic():
                result = self.process(*args, **kwargs)
            self.logger.info(f"Completed execution of service: {self.__class__.__name__}")
            return result
        except Exception as e:
            self.logger.error(f"Error executing service {self.__class__.__name__}: {str(e)}", exc_info=True)
            raise e

    def process(self, *args, **kwargs):
        """
        Core logic placeholder. Implement in subclass.
        """
        raise NotImplementedError("Subclasses must implement the process method.")
