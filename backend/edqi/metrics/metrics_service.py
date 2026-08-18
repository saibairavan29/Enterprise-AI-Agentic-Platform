from edqi.metrics.metrics_builder import MetricsBuilder
from edqi.metrics.metrics_repository import MetricsRepository

class MetricsService:
    """
    Unified entry point for modules to save and query performance and diagnostic metrics.
    """
    @classmethod
    def record_metric(cls, module_name: str, metric_name: str, value: float, metadata: dict = None):
        metric = MetricsBuilder.build_metric(module_name, metric_name, value, metadata)
        MetricsRepository.save_metric(metric)

    @classmethod
    def get_metrics(cls, module_name: str = None, metric_name: str = None) -> list:
        all_metrics = MetricsRepository.load_metrics()
        filtered = all_metrics
        if module_name:
            filtered = [m for m in filtered if m["module"] == module_name]
        if metric_name:
            filtered = [m for m in filtered if m["metric"] == metric_name]
        return filtered

    @classmethod
    def get_average(cls, module_name: str, metric_name: str) -> float:
        metrics = cls.get_metrics(module_name, metric_name)
        if not metrics:
            return 0.0
        return sum(m["value"] for m in metrics) / len(metrics)
