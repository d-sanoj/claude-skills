# Before / after: the Thursday 16:40 build

The scene is one every team knows. The numbers in it are measured, not invented: the fixture suite in `examples/fixture/` (9 tests, 4 deliberate flakes) run 100 times, and the hunt below is the real output of `scripts/flake-hunt.py` on that fixture.

## Before: the retry reflex

Thursday, 16:40. The build goes red on `test_async_result_ready`. Nobody opens the stack trace. Someone clicks retry, the second run comes back green, the PR merges, and the ticket closes without a comment.

The engineer had no evidence the failure was real, the rerun costs a fraction of a cent, and an investigation costs an afternoon. Do it two hundred times over a quarter and every instance is still individually defensible. It is also, exactly, how a real defect gets waved through: the retry button cannot tell a test that is lying from a test that is right.

The measurement says how much the retry misses. In 100 runs of the fixture, the first run -- the one the retry reflex trusts -- caught 2 of the 4 flakes and missed the other two entirely. The wall-clock test failed 29 times in 100 runs and the random test 27 times, and both passed that first run. A single run catches a 29%-flake exactly 29% of the time. "It passed" is nearly no evidence at all.

## After: the hunt

The same red build, with the skill in place. Instead of retrying, the engineer hunts:

```bash
cd examples/fixture
python3 ../../scripts/flake-hunt.py hunt . --runs 10
```

```text
# flake-hunt: 10 runs of .
tests: 9; first run failed: 2

## FLAKY: tests/test_flaky.py::test_async_result_ready
- in suite: 3/10 failed
- alone (10x): 7 failed
- classification: fails alone -- time / random / async
- evidence: failed 7/10 alone, 3/10 in the suite; source hints: sleep() -- bare sleep waiting on async work

## FLAKY: tests/test_flaky.py::test_expiry_uses_wall_clock
- in suite: 6/10 failed
- alone (10x): 6 failed
- classification: fails alone -- time / random / async
- evidence: failed 6/10 alone, 6/10 in the suite; source hints: wall clock -- depends on when the test runs

## FLAKY: tests/test_flaky.py::test_random_sample_covers_all
- in suite: 3/10 failed
- alone (10x): 3 failed
- classification: fails alone -- time / random / async
- evidence: failed 3/10 alone, 3/10 in the suite; source hints: random.* -- unseeded randomness

## FAILS-IN-SUITE: tests/test_flaky.py::test_visit_count_starts_at_zero
- in suite: 10/10 failed
- alone (10x): 0 failed
- classification: order / shared state -- passes alone, fails in suite
- evidence: passed 10/10 alone, failed 10/10 in the suite

4 suspect test(s). Report in flake-hunt-out/flake-report.md
```

Four suspects, each with a classification and the evidence for it. The async test gets fixed by waiting for the condition instead of sleeping a fixed 0.05 seconds -- the fix Luo et al. found actually removes the flakiness, where lengthening the sleep never did (0 of 20 sleep fixes removed it; 23 of 42 waitFor fixes did). The wall-clock test gets an injected clock. The random test gets a seed, logged so the failing draw reproduces. The order test gets a fresh fixture per test instead of module-level state. Each one is quarantined with a ticket, an owner, and a deadline while the fix lands.

## The borderline that stays honest

The same measurement has a case the skill refuses to overclaim. The wall-clock test passed all 10 alone-runs in the 100-run measurement's isolation step (0 failed in 10), while failing 29 times in 100 suite runs. A classifier that trusted "passes alone" would have called it order-dependent -- wrong. The skill's classifier reports the source hint (`time.time(` -- wall clock) next to the alone-run count, and says plainly that a low-rate flake can pass a short alone-run by luck (a 29% flake passes 10 in a row about 3% of the time). "Passes alone" is a leading hypothesis, not a verdict, and the hint is what separates the two cases. A tool that is certain about uncertain evidence is worse than one that says it does not know.
