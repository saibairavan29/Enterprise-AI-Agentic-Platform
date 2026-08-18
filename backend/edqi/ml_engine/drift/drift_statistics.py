import os
import json

class DriftStatistics:
    """
    Computes summary averages over compiled model drift histories list.
    """
    @staticmethod
    def get_drift_history_path() -> str:
        curr = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(curr, "reports", "drift", "drift_history.json")

    @classmethod
    def compile_drift_statistics(cls) -> dict:
        path = cls.get_drift_history_path()
        if not os.path.exists(path):
            return {
                "total_drift_checks": 0,
                "average_drift_percentage": 0.0,
                "severity_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            }
        try:
            with open(path, 'r') as f:
                history = json.load(f)
        except Exception:
            history = []

        total_checks = len(history)
        if total_checks == 0:
            return {
                "total_drift_checks": 0,
                "average_drift_percentage": 0.0,
                "severity_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
            }

        avg_drift = sum(item["metadata"]["drift_percentage"] for item in history) / total_checks
        severities = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for item in history:
            sev = item["metadata"]["drift_severity"]
            if sev in severities:
                severities[sev] += 1

        return {
            "total_drift_checks": total_checks,
            "average_drift_percentage": round(avg_drift, 2),
            "severity_counts": severities,
            "last_check": history[-1]["metadata"]["generated_at"] if history else None
        }
