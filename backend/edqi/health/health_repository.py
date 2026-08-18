import os
import json
from datetime import datetime

class HealthRepository:
    """
    Handles file persistency operations for the Enterprise Health scoring histories.
    """
    @staticmethod
    def get_health_dir() -> str:
        curr = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(curr, "reports", "health")
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def save_health_report(cls, report_data: dict):
        health_dir = cls.get_health_dir()
        date_folder = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Save active health_score.json
        json_path = os.path.join(health_dir, "health_score.json")
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=4)

        # Archive snapshot folder
        history_dir = os.path.join(health_dir, "history", date_folder)
        os.makedirs(history_dir, exist_ok=True)
        with open(os.path.join(history_dir, "health_score.json"), 'w') as f:
            json.dump(report_data, f, indent=4)

        # Update health_history.json list
        history_path = os.path.join(health_dir, "health_history.json")
        history_list = []
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    history_list = json.load(f)
            except Exception:
                history_list = []
        history_list.append(report_data)
        with open(history_path, 'w') as f:
            json.dump(history_list, f, indent=4)

    @classmethod
    def load_history(cls) -> list:
        history_path = os.path.join(cls.get_health_dir(), "health_history.json")
        if not os.path.exists(history_path):
            return []
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []
