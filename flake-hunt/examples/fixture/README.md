# Fixture: a suite with four deliberate flakes

A 9-test pytest suite for measuring flakiness. Four tests are stable
(the control group); four tests are flaky on purpose, one per classic
cause; and one test exists only to mutate shared state, so the
order-dependent test has something to trip on. Run it with the skill:

```bash
cd examples/fixture
python3 ../../scripts/flake-hunt.py hunt . --runs 10
```

## The tests

| Test | Cause | Designed fail rate |
|---|---|---|
| `test_expiry_uses_wall_clock` | wall clock (`time.time() % 10 < 3`) | ~30% |
| `test_random_sample_covers_all` | unseeded `random.random()` | ~25% |
| `test_async_result_ready` | bare `sleep(0.05)` before reading an async result that takes uniform(0, 0.1)s | ~50% |
| `test_visit_count_starts_at_zero` | order / shared state: passes alone, fails in the suite | ~100% in suite, 0% alone |
| `test_records_a_visit` | the test that mutates the shared state (runs first) | 0% |
| 4 tests in `test_stable.py` | -- | 0% |

## Measured rates (100 suite runs, 2026-11-25)

Measured with `measure-flakes.py`, shipped with the blog post
["The test that passes until it doesn't"](https://sanoj.dev/blog/the-test-that-passes-until-it-doesnt/).
The full results are in `flake-rates.json` with the post.

| Test | Failed / 100 runs | Alone (10x) |
|---|---|---|
| test_async_result_ready | 56 | 7 failed |
| test_expiry_uses_wall_clock | 29 | 0 failed |
| test_random_sample_covers_all | 27 | 2 failed |
| test_visit_count_starts_at_zero | 100 | 0 failed |
| 4 stable tests | 0 | -- |

The first of the 100 runs caught 2 of the 4 flakes. A 10-run hunt
caught all 4. The stable tests failed 0 times in 100 suite runs and
0 times in a 200-execution stable-only control.

The rates are *designed*, then *measured*: the design column is what
the code aims at (a 3-in-10 wall-clock window, a 1-in-4 random draw,
a 50/50 race), and the measured column is what 100 runs actually
produced. Sampling variation is real -- the async test was designed
at 50% and measured 56% -- which is itself the point: a flake's rate
is a property you measure, not a number you assume.
