from .base import BaseTransformer

class BooleanTransformer(BaseTransformer):
    """
    Transformer responsible for boolean standardizations:
    Maps yes/no/enabled/disabled/Y/N strings to clean Python boolean values.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None:
            return val

        if isinstance(val, bool):
            return val

        original = val
        mappings = rules.get("boolean_mappings", {})
        s = str(val).lower().strip()

        if s in mappings:
            standardized = mappings[s]
            if standardized != original:
                changes_list.append({
                    "field": field_name,
                    "original": original,
                    "standardized": standardized,
                    "rule": "BOOLEAN_STANDARD"
                })
            return standardized

        return original
