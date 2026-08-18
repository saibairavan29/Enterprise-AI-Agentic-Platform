import time
from contextlib import contextmanager

@contextmanager
def measure_duration():
    """
    Context manager to calculate execution elapsed duration in seconds.
    """
    timer = {"start": time.perf_counter(), "elapsed": 0.0}
    yield timer
    timer["elapsed"] = round(time.perf_counter() - timer["start"], 4)
