"""Tiny demo app for the flake-hunt fixture.

Four of the nine tests in tests/ are deliberately flaky, each in a
different classic way (Luo et al., FSE 2014: async wait, test order
dependency, time, randomness). The flakiness is in the *tests*, not
here -- except for start_double, which models real async work whose
completion time the caller cannot control.
"""

import random
import threading
import time


def add(a, b):
    return a + b


def double(x):
    return 2 * x


# --- shared state: the order-dependence trap -------------------------------
_counter = {"visits": 0}


def record_visit():
    _counter["visits"] += 1
    return _counter["visits"]


def visits():
    return _counter["visits"]


# --- async work: completes after a delay the caller cannot see ------------
class _DoubleJob:
    def __init__(self, x):
        self._out = {}
        # Completion time drawn uniformly from 0..0.1s: the test that
        # sleeps a fixed 0.05s before reading the result fails about
        # half the time. That is the flake, and it is in the test.
        delay = random.uniform(0, 0.1)

        def work():
            time.sleep(delay)
            self._out["v"] = 2 * x

        self._thread = threading.Thread(target=work)
        self._thread.start()

    def result(self):
        return self._out.get("v")


def start_double(x):
    return _DoubleJob(x)
