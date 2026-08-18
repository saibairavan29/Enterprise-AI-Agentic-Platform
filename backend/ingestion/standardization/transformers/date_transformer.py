import re
from datetime import datetime
from .base import BaseTransformer

class DateTransformer(BaseTransformer):
    """
    Transformer responsible for date standardizations:
    Converts various string expressions into ISO-8601 (YYYY-MM-DD) date records.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None:
            return val

        if isinstance(val, datetime):
            iso_date = val.date().isoformat()
            changes_list.append({
                "field": field_name,
                "original": str(val),
                "standardized": iso_date,
                "rule": "ISO_DATE"
            })
            return iso_date

        s = str(val).strip()
        if not s:
            return None

        # If already fits target format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s

        original = val
        date_formats = rules.get("date_formats", [])

        # Try parsing via configuration date_formats list
        for fmt in date_formats:
            try:
                dt = datetime.strptime(s, fmt)
                iso_date = dt.date().isoformat()
                changes_list.append({
                    "field": field_name,
                    "original": original,
                    "standardized": iso_date,
                    "rule": "ISO_DATE"
                })
                return iso_date
            except ValueError:
                continue

        # Loose parsing fallback using dateutil (if installed)
        try:
            from dateutil import parser
            dt = parser.parse(s)
            iso_date = dt.date().isoformat()
            changes_list.append({
                "field": field_name,
                "original": original,
                "standardized": iso_date,
                "rule": "ISO_DATE"
            })
            return iso_date
        except Exception:
            # Leave invalid dates unchanged, allowing later checks to report anomalies
            return original
