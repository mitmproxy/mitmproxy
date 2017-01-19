import os
from contextlib import contextmanager


@contextmanager
def chdir(dir):
    orig_dir = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(orig_dir)
