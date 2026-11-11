import time


def retry_with_backoff(fn, tries=3):
    """Call fn. If it raises, wait and try again, doubling the wait each
    time. Gives up after `tries` attempts and re-raises the last error."""
    wait = 1
    for attempt in range(tries):
        try:
            return fn()
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(wait)
            wait *= 2
