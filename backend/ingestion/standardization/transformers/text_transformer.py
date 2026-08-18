import unicodedata
import re
from .base import BaseTransformer

class TextTransformer(BaseTransformer):
    """
    Transformer responsible for string cleanup:
    unicode normalizations, smart quotes converter, dash formatting, spacing collapse, and casings.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None or not isinstance(val, str):
            return val

        original = val
        text_rules = rules.get("text_rules", {})

        # 1. Unicode normalization
        unicode_norm = text_rules.get("unicode_normalization", "NFKC")
        val = unicodedata.normalize(unicode_norm, val)

        # 2. Convert smart quotes
        if text_rules.get("convert_smart_quotes", True):
            val = val.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        # 3. Normalize dash characters
        if text_rules.get("normalize_dashes", True):
            val = val.replace("–", "-").replace("—", "-")

        # 4. Remove control and invisible characters (excluding newlines)
        val = re.sub(r'[\u200b-\u200d\ufeff\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', val)

        # 5. Normalize line breaks and tabs
        val = val.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

        # 6. Trim leading and trailing whitespace
        val = val.strip()

        # 7. Collapse multiple consecutive spaces
        if text_rules.get("collapse_spaces", True):
            val = re.sub(r'[ ]+', ' ', val)

        # 8. Casing adjustments
        field_casings = text_rules.get("field_casings", {})
        base_field = field_name.split(".")[-1]
        casing = field_casings.get(base_field, text_rules.get("default_casing", "none"))

        if casing == "upper":
            val = val.upper()
        elif casing == "lower":
            val = val.lower()
        elif casing == "title":
            val = val.title()

        if val != original:
            changes_list.append({
                "field": field_name,
                "original": original,
                "standardized": val,
                "rule": "TEXT_STANDARD"
            })

        return val
