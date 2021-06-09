from contextlib import contextmanager
from timeit import default_timer as timer


@contextmanager
def in_time(seconds):
    start_ts = timer()
    yield
    ts_diff = timer() - start_ts
    assert ts_diff < seconds, (ts_diff, seconds)
