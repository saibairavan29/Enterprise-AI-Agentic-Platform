import time
from contextlib import contextmanager

@contextmanager
def measure_time():
    """
    Context manager measuring execution time in float seconds.
    Modifies the yielded result dictionary once execution leaves the code block.
    """
    result = {"elapsed": 0.0}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed"] = round(time.perf_counter() - start, 4)
