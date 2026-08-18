import re
from .base import BaseTransformer

class NumericTransformer(BaseTransformer):
    """
    Transformer responsible for parsing numeric expressions:
    currency sign removals, negative brackets conversion, percentage division, and float/int conversions.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None:
            return val

        # Already a numeric type, return directly
        if isinstance(val, (int, float)):
            return val

        if not isinstance(val, str):
            return val

        original = val
        num_rules = rules.get("numeric_rules", {})
        s = val.strip()

        if not s:
            return None

        # 1. Negative brackets detection, e.g. (5,000) -> -5000
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            s = s[1:-1].strip()

        # 2. Currency symbol stripping
        for sym in num_rules.get("currency_symbols", ["$", "€", "£", "¥", "₹"]):
            s = s.replace(sym, "")

        # 3. Separator normalize (strips thousands comma, converts comma decimal notation if applicable)
        if num_rules.get("strip_separators", True):
            if "," in s and "." in s:
                s = s.replace(",", "")
            elif "," in s:
                # If there are multiple commas, or comma matches thousands formatting
                if s.count(",") > 1 or re.search(r',\d{3}$', s):
                    s = s.replace(",", "")
                else:
                    # Resolve comma as decimal dot representation (European format)
                    s = s.replace(",", ".")

        # 4. Percent scale notation, e.g. 12.5% -> 0.125
        is_percent = False
        if s.endswith("%"):
            is_percent = True
            s = s[:-1].strip()

        # 5. Conversion check
        try:
            parsed_val = float(s)
            if is_negative:
                parsed_val = -parsed_val
            if is_percent:
                parsed_val = parsed_val / 100.0

            # Map whole float floats back to pure int
            if parsed_val.is_integer() and not is_percent:
                parsed_val = int(parsed_val)

            if parsed_val != original:
                changes_list.append({
                    "field": field_name,
                    "original": original,
                    "standardized": parsed_val,
                    "rule": "NUMERIC_STANDARD"
                })
            return parsed_val
        except ValueError:
            # Keep original value if not convertible
            return original
PostgresNumericTransformer = NumericTransformer  # Database mapping alias
