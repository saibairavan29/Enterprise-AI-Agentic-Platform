import json
import os

class MappingLoader:
    """
    Loader responsible for reading mapping rules from mapping_rules.json configuration.
    """
    def __init__(self):
        self.rules_path = os.path.join(os.path.dirname(__file__), "mapping_rules.json")

    def load_rules(self):
        """
        Loads and returns the json dictionary of mapping rules.
        """
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load mapping rules from config {self.rules_path}: {str(e)}")
