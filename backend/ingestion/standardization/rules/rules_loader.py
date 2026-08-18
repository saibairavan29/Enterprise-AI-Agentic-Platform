import json
import os

class RulesLoader:
    """
    Loader responsible for reading standardization configurations from JSON.
    """
    def __init__(self):
        self.rules_path = os.path.join(os.path.dirname(__file__), "standardization_rules.json")

    def load_rules(self):
        """
        Loads and returns the json dictionary of standardization rules.
        """
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load standardization rules from {self.rules_path}: {str(e)}")
