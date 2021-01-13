import functools
import time
from ref import runtime_log


def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        with open(runtime_log, 'a') as t:
            t.write(F"Elapsed time: {elapsed_time:0.4f} seconds for {func.__name__}\n")
        return value
    return wrapper_timer
