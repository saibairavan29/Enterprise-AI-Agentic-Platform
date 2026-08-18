import logging
import traceback

logger = logging.getLogger("enterprise.edqi.ml_engine")

class MLLogger:
    """
    Centralized logging client coordinating logging formats for the ML Engine.
    """
    @staticmethod
    def info(msg: str, *args, **kwargs):
        logger.info(f"[ML INFO] {msg}", *args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        logger.warning(f"[ML WARNING] {msg}", *args, **kwargs)

    @staticmethod
    def error(msg: str, *args, **kwargs):
        logger.error(f"[ML ERROR] {msg}", *args, **kwargs)

    @staticmethod
    def exception(msg: str, exc: Exception, *args, **kwargs):
        logger.error(f"[ML EXCEPTION] {msg}: {str(exc)}", exc_info=True, *args, **kwargs)

    @staticmethod
    def dataset(msg: str, *args, **kwargs):
        logger.info(f"[ML DATASET] {msg}", *args, **kwargs)

    @staticmethod
    def training(msg: str, *args, **kwargs):
        logger.info(f"[ML TRAINING] {msg}", *args, **kwargs)

    @staticmethod
    def evaluation(msg: str, *args, **kwargs):
        logger.info(f"[ML EVALUATION] {msg}", *args, **kwargs)

    @staticmethod
    def prediction(msg: str, *args, **kwargs):
        logger.info(f"[ML PREDICTION] {msg}", *args, **kwargs)

    @staticmethod
    def model_lifecycle(msg: str, *args, **kwargs):
        logger.info(f"[ML LIFECYCLE] {msg}", *args, **kwargs)
