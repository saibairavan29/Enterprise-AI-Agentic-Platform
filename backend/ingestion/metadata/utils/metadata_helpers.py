from datetime import datetime

def parse_iso_timestamp(val):
    """
    Safely attempts parsing date strings to datetime instances.
    Returns None if parsing fails.
    """
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except ValueError:
        return None
