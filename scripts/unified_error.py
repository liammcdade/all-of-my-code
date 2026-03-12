import logging
import functools
import sys

def error_reporter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}", exc_info=True)
            print(f"\n[ERROR] {e}", file=sys.stderr)
            return None
    return wrapper

from contextlib import contextmanager

@contextmanager
def error_handling_context():
    try:
        yield
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        print(f"\n[ERROR] {e}", file=sys.stderr) 