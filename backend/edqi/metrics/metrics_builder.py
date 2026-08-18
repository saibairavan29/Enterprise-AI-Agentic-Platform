import time
from datetime import datetime

class MetricsBuilder:
    """
    Standardizes validation and schema representation for all system metrics.
    """
    @staticmethod
    def build_metric(module_name: str, metric_name: str, value: float, metadata: dict = None) -> dict:
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "module": str(module_name),
            "metric": str(metric_name),
            "value": float(value),
            "metadata": metadata or {}
        }
