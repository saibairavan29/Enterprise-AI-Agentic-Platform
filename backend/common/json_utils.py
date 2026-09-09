import json
import datetime
import math

def sanitize_json_obj(obj):
    """
    Recursively converts non-JSON-serializable objects (such as pandas.Timestamp,
    numpy datatypes, datetime instances, NaNs, and NaTs) into standard JSON-serializable primitives.
    Preserves semantic data types (int, float, bool, str, list, dict, None).
    """
    # 1. None check
    if obj is None:
        return None

    # 2. Standard JSON-safe Python primitives
    if isinstance(obj, bool):
        return bool(obj)

    if isinstance(obj, int):
        return int(obj)

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)

    if isinstance(obj, str):
        return obj

    # 3. Python datetime/date/time
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()

    # 4. Datetime-like objects with isoformat (e.g., pandas.Timestamp)
    if hasattr(obj, 'isoformat') and callable(getattr(obj, 'isoformat')):
        try:
            if hasattr(obj, 'is_nat') and getattr(obj, 'is_nat'):
                return None
            return obj.isoformat()
        except Exception:
            return str(obj)

    # 5. NumPy scalars or objects with .item() (e.g. np.int64, np.float64, np.bool_, np.datetime64)
    if hasattr(obj, 'item') and callable(getattr(obj, 'item')):
        try:
            val = obj.item()
            if val is not obj:
                return sanitize_json_obj(val)
        except Exception:
            pass

    # 6. Dictionaries / Mappings
    if isinstance(obj, dict):
        return {str(k): sanitize_json_obj(v) for k, v in obj.items()}

    # 7. Sequences / Arrays / Iterables (list, tuple, set, numpy.ndarray, pandas.Series, pandas.Index)
    if isinstance(obj, (list, tuple, set)) or (hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, dict))):
        try:
            return [sanitize_json_obj(item) for item in obj]
        except Exception:
            pass

    # 8. Scalar missing-value detection (guarded against arrays/non-booleans)
    try:
        import pandas as pd
        res = pd.isna(obj)
        if isinstance(res, bool) and res:
            return None
    except Exception:
        pass

    # 9. Fallback to string representation for remaining custom non-serializable objects (e.g. Timedelta, UUID)
    return str(obj)



def find_non_serializable_path(obj, path=""):
    """
    Recursively inspects obj to locate the exact nested key path and type of any object
    that cannot be serialized by standard json.dumps.
    """
    if obj is None or isinstance(obj, (int, float, bool, str)):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return path or "root", type(obj).__name__, "NaN/Infinity float"
        return None

    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else str(k)
            res = find_non_serializable_path(v, current_path)
            if res:
                return res
        return None

    if isinstance(obj, (list, tuple, set)):
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]"
            res = find_non_serializable_path(item, current_path)
            if res:
                return res
        return None

    return path or "root", type(obj).__name__, str(obj)


def enforce_json_boundary(obj, label="payload"):
    """
    Establishes a hard JSON-serialization boundary for database JSONFields.
    1. Sanitizes obj recursively via sanitize_json_obj(obj).
    2. Runs json.dumps() to validate total JSON-serializability before passing to ORM.
    3. If json.dumps fails, pinpoints the exact nested path and raises a diagnostic ValueError.
    Returns the sanitized, JSON-validated payload object.
    """
    sanitized = sanitize_json_obj(obj)
    try:
        json.dumps(sanitized)
        return sanitized
    except Exception as exc:
        bad_path, bad_type, bad_val = find_non_serializable_path(sanitized)
        raise ValueError(
            f"JSON boundary violation in '{label}' at path '{bad_path}': "
            f"Object of type '{bad_type}' ({bad_val}) is not JSON serializable. Original Exception: {str(exc)}"
        ) from exc


