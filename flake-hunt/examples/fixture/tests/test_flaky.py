"""Four deliberately flaky tests, one per classic cause.

Each test is labelled with its cause and its designed failure rate.
The rates are *designed*, not measured: the measurement script
(measure-flakes.py, shipped with the blog post) runs the suite 100
times and reports what actually happened. The point of the fixture
is that a single run of this suite usually looks green while the
suite is, in fact, unreliable -- exactly the situation flake-hunt
exists to catch.

Design notes:
- TIME: fails when the wall clock is in the first 3 seconds of a
  10-second window, i.e. about 30% of runs. A real version of this
  is a test that checks "expires at end of day" or date formatting
  near midnight.
- RANDOM: unseeded random.random() below 0.25, i.e. about 25% of
  runs. A real version is a test that samples data without a seed.
- ASYNC: the worker finishes after a uniform(0, 0.1)s delay and the
  test sleeps a fixed 0.05s before reading, i.e. about 50% of runs.
  A real version is any `sleep(N); assert ready` pattern.
- ORDER: passes alone, fails in the suite, because test_records_a_
  visit (defined first, so it runs first) mutates module-level state
  that test_visit_count_starts_at_zero assumes is fresh. A real
  version is any test that depends on another test's leftovers.
"""

import random
import time

from app import record_visit, start_double, visits


def test_expiry_uses_wall_clock():
    # TIME -- designed fail rate ~30%.
    now = time.time()
    assert (now % 10) >= 3, "discount code unexpectedly expired"


def test_random_sample_covers_all():
    # RANDOM -- designed fail rate ~25%. No seed on purpose.
    assert random.random() >= 0.25, "sample missed the target bucket"


def test_async_result_ready():
    # ASYNC WAIT -- designed fail rate ~50%.
    job = start_double(21)
    time.sleep(0.05)  # bare sleep: the classic mistake (Fowler 2011)
    assert job.result() == 42, "async result not ready after sleep"


def test_records_a_visit():
    # Runs first (definition order). Mutates module-level state.
    assert record_visit() == 1


def test_visit_count_starts_at_zero():
    # ORDER -- fails ~100% in the suite, passes ~100% alone.
    assert visits() == 0, "shared counter was not reset"
