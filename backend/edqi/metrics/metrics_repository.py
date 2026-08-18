import os
import json
from datetime import datetime

class MetricsRepository:
    """
    Manages filesystem persistency for compiled metrics history payloads.
    """
    @staticmethod
    def get_file_path() -> str:
        curr = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(curr, "reports", "performance")
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, "metrics_repository.json")

    @classmethod
    def save_metric(cls, metric_data: dict):
        path = cls.get_file_path()
        metrics = []
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    metrics = json.load(f)
            except Exception:
                metrics = []
        metrics.append(metric_data)
        with open(path, 'w') as f:
            json.dump(metrics, f, indent=4)

        # Automatically regenerate all performance and project statistics reports
        from edqi.ml_engine.services.performance_service import PerformanceService
        try:
            PerformanceService.generate_all_reports()
        except Exception as e:
            # Prevent crashes if platforms libraries/imports have issues in certain environments
            pass

    @classmethod
    def load_metrics(cls) -> list:
        path = cls.get_file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return []
