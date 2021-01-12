import functools
import time
import os
from ref import raw_data_dir

# make a blank file on import that is appended to by 'timer'
log_file = os.path.join(raw_data_dir, "log_file.txt")
f = open(log_file, 'w')
f.close()


def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        tic = time.perf_counter()
        value = func(*args, **kwargs)
        toc = time.perf_counter()
        elapsed_time = toc - tic
        with open(log_file, 'a') as t:
            t.write(F"Elapsed time: {elapsed_time:0.4f} seconds for {func.__name__}\n")
        return value
    return wrapper_timer
