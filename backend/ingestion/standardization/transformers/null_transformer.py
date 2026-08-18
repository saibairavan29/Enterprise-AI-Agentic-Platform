from .base import BaseTransformer

class NullTransformer(BaseTransformer):
    """
    Transformer responsible for null standardizations:
    Maps custom empty string representation keywords to None.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None:
            return None

        original = val
        null_vals = rules.get("null_values", ["null", "none", "n/a", "na", "unknown", "", " "])
        s = str(val).lower().strip()

        if s in null_vals:
            changes_list.append({
                "field": field_name,
                "original": original,
                "standardized": None,
                "rule": "NULL_STANDARD"
            })
            return None

        return val
