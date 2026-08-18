import os
import json
from datetime import datetime

class LifecycleHistoryLogger:
    """
    Manages audit logging of model lifecycle events (e.g. TRAINED, ACTIVATED, RETIRED).
    """
    @staticmethod
    def get_file_path() -> str:
        curr = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(curr, "reports", "manifests")
        os.makedirs(path, exist_ok=True)
        return os.path.join(path, "model_lifecycle.json")

    @classmethod
    def log_event(cls, model_version: str, event: str, metadata: dict = None):
        path = cls.get_file_path()
        events = []
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    events = json.load(f)
            except Exception:
                events = []
        
        events.append({
            "version": str(model_version),
            "event": str(event),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {}
        })
        
        with open(path, 'w') as f:
            json.dump(events, f, indent=4)

    @classmethod
    def get_events(cls) -> list:
        path = cls.get_file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            return []
