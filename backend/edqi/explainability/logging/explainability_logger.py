import logging

logger = logging.getLogger("enterprise.edqi.explainability")

class ExplainabilityLogger:
    """
    Centralized logging coordinator for explainability, recommendation, and cache actions.
    """
    @staticmethod
    def info(msg: str, *args, **kwargs):
        logger.info(f"[XAI INFO] {msg}", *args, **kwargs)

    @staticmethod
    def warning(msg: str, *args, **kwargs):
        logger.warning(f"[XAI WARNING] {msg}", *args, **kwargs)

    @staticmethod
    def error(msg: str, *args, **kwargs):
        logger.error(f"[XAI ERROR] {msg}", *args, **kwargs)

    @staticmethod
    def exception(msg: str, exc: Exception, *args, **kwargs):
        logger.error(f"[XAI EXCEPTION] {msg}: {str(exc)}", exc_info=True, *args, **kwargs)

    @staticmethod
    def prediction(msg: str, *args, **kwargs):
        logger.info(f"[XAI PREDICTION] {msg}", *args, **kwargs)

    @staticmethod
    def cache_hit(prediction_id: str, *args, **kwargs):
        logger.info(f"[XAI CACHE HIT] Explanation cache resolved for prediction: {prediction_id}", *args, **kwargs)

    @staticmethod
    def cache_miss(prediction_id: str, *args, **kwargs):
        logger.info(f"[XAI CACHE MISS] Cache miss for prediction: {prediction_id}. Initializing Explainer.", *args, **kwargs)

    @staticmethod
    def explainer_run(algorithm: str, duration_ms: float, *args, **kwargs):
        logger.info(f"[XAI RUN] Explainer '{algorithm}' executed in {round(duration_ms, 2)} ms.", *args, **kwargs)

    @staticmethod
    def fallback_used(reason: str, *args, **kwargs):
        logger.warning(f"[XAI FALLBACK] Fallback explainer initiated (Reason: {reason}).", *args, **kwargs)

    @staticmethod
    def recommendation_generated(recommendations_count: int, *args, **kwargs):
        logger.info(f"[XAI RECOMMENDATIONS] Successfully compiled {recommendations_count} suggestions.", *args, **kwargs)

    @staticmethod
    def api_request(method: str, path: str, duration_ms: float, *args, **kwargs):
        logger.info(f"[XAI API] API Request {method} {path} handled in {round(duration_ms, 2)} ms.", *args, **kwargs)
