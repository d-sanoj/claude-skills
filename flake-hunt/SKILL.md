---
name: flake-hunt
description: Find the flaky test before it eats your morning. Use when a build goes red and passes on retry, when a test fails in CI but passes locally, when a PR's only red check is "that test again", or when you want to know whether your suite is trustworthy at all. Runs the suite N times, names every test that changed its answer on unchanged code, isolates each suspect alone to separate time/random/async flakes from order/shared-state ones, and quarantines what it finds with an owner and a deadline -- with a script that does the mechanical part deterministically.
---

# Flake-hunt: a green rerun is not a repair

Thursday, 16:40. The build goes red on an integration test. Nobody opens the stack trace. Someone clicks retry, the second run comes back green, the PR merges. The failure was real -- a race in the code the test was covering -- and it shipped, because the retry button cannot tell a test that is lying from a test that is right.

A flaky test is one that both passes and fails on the same code: Google's working definition, from John Micco's 2016 post on the Google Testing Blog. The scale is not small. At Google, about 1.5% of all test runs reported a flaky result, almost 16% of tests had some level of flakiness, and about 84% of the pass-to-fail transitions in post-submit testing involved a flaky test. The largest study of the causes, Luo et al. (FSE 2014, 201 commits fixing flaky tests across 51 Apache projects, 161 classified), found three causes behind 77% of the fixes: async wait 45%, concurrency 20%, test order dependency 12%. And most flaky tests -- 78% in that study -- were flaky from the revision that introduced them. They are usually born, not acquired.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/flake-hunt.py" hunt tests/ --runs 10
python3 "$S/flake-hunt.py" isolate tests/test_x.py::test_y --runs 5
python3 "$S/flake-hunt.py" quarantine tests/test_x.py::test_y
```

Tools: Python 3.10+, pytest. No packages, no network, no model calls.

## The measurement behind it

A fixture suite of 9 tests (in `examples/fixture/`): 4 stable tests, 4 flaky tests -- one per classic cause -- and one test whose only job is to mutate shared state so the order-dependent test can fail. The flakes are a wall-clock test (~30% fail rate by design), an unseeded-random test (~25%), a bare-sleep async test (~50%), and an order-dependent test (fails in the suite, passes alone). I ran the suite 100 times with the blog post's `measure-flakes.py` (shipped with the post, ["The test that passes until it doesn't"](https://sanoj.dev/blog/the-test-that-passes-until-it-doesnt/) (November 25, 2026)):

| Test | Cause | Failed / 100 runs | Alone (10x) |
|---|---|---|---|
| test_async_result_ready | async wait | 56 | 7 failed |
| test_expiry_uses_wall_clock | wall clock | 29 | 0 failed |
| test_random_sample_covers_all | unseeded random | 27 | 2 failed |
| test_visit_count_starts_at_zero | order / shared state | 100 | 0 failed |
| 4 stable tests | -- | 0 | -- |

Two things worth noticing. First, the single run that opens the story caught 2 of the 4 flakes and missed the other two -- a single run catches a 29%-flake exactly 29% of the time, so "it passed" is nearly no evidence at all. Second, the wall-clock test passed all 10 alone-runs by luck (a 29% flake passes 10 in a row about 3% of the time) -- which is why the classifier treats "passes alone" as a leading hypothesis, not a verdict, when the source also hints at a low-rate flake: it reports the source hints alongside, and a low-rate flake can hide behind a short alone-run. The control groups stayed clean: the 4 stable tests failed 0 times in 100 suite runs and 0 times in 200 executions of a stable-only control, and 12 real tests from the author's local-rag repo (test_bm25.py, test_rrf.py) ran 20 times each -- 240 executions, 0 failures. The method does not cry wolf.

The detection math is the whole argument for hunting instead of retrying. For a test that fails with probability p, the chance that N runs catch it is 1 - (1 - p)^N:

| Fail rate p | 1 run | 5 runs | 10 runs | 20 runs | 50 runs |
|---|---|---|---|---|---|
| 1% | 1% | 5% | 10% | 18% | 40% |
| 5% | 5% | 23% | 40% | 64% | 92% |
| 10% | 10% | 41% | 65% | 88% | 99% |
| 25% | 25% | 76% | 94% | 100% | 100% |

A 10% flake -- the kind that ruins one morning a week -- passes a single run 90% of the time and a 10-run hunt still misses it a third of the time. Ten runs is the default because it is cheap, not because it is enough: for a suite you are about to trust with a release, run 20. The hunt on this fixture (10 runs) found all four suspects; the 100-run measurement is what set the rates.

## 1. Hunt: run the suite N times

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

## FAILS-IN-SUITE: tests/test_flaky.py::test_visit_count_starts_at_zero
- in suite: 10/10 failed
- alone (10x): 0 failed
- classification: order / shared state -- passes alone, fails in suite
- evidence: passed 10/10 alone, failed 10/10 in the suite

4 suspect test(s). Report in flake-hunt-out/flake-report.md
```

Exit 0 means no test changed its answer in N runs. Exit 1 means at least one did, and the run is not done until the list is empty. The report lands in `flake-hunt-out/flake-report.md` and `.json`. A test that fails every run is not flaky by the definition -- it never passes -- but the hunt still lists it as FAILS-IN-SUITE and isolates it, because a test that fails 10/10 in the suite and 0/10 alone is the order-dependence signature, and that is exactly what the fixture's order test does.

Run the hunt on the tests you are about to trust, not on the whole repo every time: the suite that gates the merge, the file you just touched, the directory whose tests keep going red. Ten runs of a fast unit suite costs seconds; ten runs of an end-to-end suite costs a lunch break. That is the trade-off to price, not a reason to run it once.

## 2. Isolate: run the suspect alone

```bash
python3 ../../scripts/flake-hunt.py isolate tests/test_flaky.py::test_async_result_ready --runs 5
```

```text
tests/test_flaky.py::test_async_result_ready: 3 passed, 2 failed in 5 runs alone
FLAKY: fails alone -- time, random, or async.
```

Isolation is the one experiment that separates the two families. A test that fails alone has its non-determinism inside itself: the clock, an unseeded random draw, a sleep that ends before the work does. A test that passes alone every time but fails in the suite gets its non-determinism from its neighbours: shared state, a file, a database row, a test that ran first. Run it alone at least 5 times; 10 is better, because a low-rate flake passes a short alone-run by luck -- the fixture's wall-clock test did exactly that (0 failed in 10 alone-runs, 29 in 100 suite runs), and the classifier says so instead of calling it order-dependent.

## 3. The rules (what the script does, and what to do by hand)

**R1 -- A rerun that passes is evidence, not a fix.** The retry button answers "did it pass this time", and a 10% flake passes 90% of the time. Never merge on a green rerun of a red test without a hunt. If the test failed once, it is a suspect until N runs say otherwise.

**R2 -- Name the flake before fixing it.** Hunt first, then isolate, then classify. Fixing before classifying is how a sleep gets lengthened from 0.05s to 0.5s -- which does not fix the flake, it just makes it rarer (Luo et al.: of 20 fixes in their study that added or changed a `sleep`, zero removed the flakiness; of the 42 that used a `waitFor`, 23 did).

**R3 -- Fix the test, not the code, unless the failure is real.** Most flakes are bugs in the test: the test waits wrong, seeds nothing, shares state. But a flaky test can also be the only witness to a real race in the product -- the async test in the fixture fails because the test sleeps, but a concurrency flake that fails more on machines with more cores may be a genuine data race. Read the failure before deciding which side is wrong. A flake you "fix" by deleting the test is a bug report you threw away.

**R4 -- Quarantine is a waiting room with an exit.** A confirmed flaky test leaves the merge-blocking suite the same day it is found, into a quarantined suite that still runs and still reports, with a ticket, an owner, and a deadline (Fowler 2011: "Place any non-deterministic test in a quarantined area. (But fix quarantined tests quickly.)"). The script prints the entry:

```bash
python3 scripts/flake-hunt.py quarantine tests/test_flaky.py::test_x
```

```text
@pytest.mark.flaky(reason="fails alone -- time / random / async")
# Ticket: [flake] tests/test_flaky.py::test_x -- fails alone ...
```

It prints the marker; it does not edit your files. The owner pastes it in and files the ticket. Cap the quarantine (Fowler suggests a numeric limit, e.g. 8 tests) and a deadline (a week): a quarantine without a cap becomes a second suite nobody reads, and a flaky test that lives in quarantine is a test that no longer guards anything.

**R5 -- Fix by cause, not by symptom.** The fix depends on the classification, and the wrong fix is worse than no fix because it looks like a fix:

| Classification | Fix | Never |
|---|---|---|
| Async wait | wait for the condition (poll until ready, or a callback), not for a number of seconds | lengthen the sleep |
| Wall clock | inject the clock; test fixed dates on purpose | assert on `now()` |
| Unseeded random | seed it and log the seed, so the failing seed reproduces | delete the random case |
| Order / shared state | fresh fixture per test; every test creates its own data | run tests in a fixed order and call it done |
| Concurrency | fix the race -- in the test or, if it is real, in the code | add a sleep to "let it settle" |
| Remote service | use a test double you control | retry the network and hope |

**R6 -- Three hunts, then hand to a human.** If the same test is still flaky after three fix attempts, stop and hand over: the cause is not in the list above, the test is testing something inherently non-deterministic (a real clock, a live service, a GPU), or the flake is a real bug that needs a design change. Looping a fourth time just re-rolls the same dice.

## 4. What this does not do

- **It does not prove a suite has no flakes.** A 10-run hunt misses a 1% flake 90% of the time (see the table). Absence of evidence is not evidence of absence; it is evidence about flakes above a certain rate. Say which rate your hunt could see: 10 runs sees a 25% flake, barely sees a 5% one, and does not see a 1% one.
- **It does not fix the flake.** It names it, isolates it, and classifies it. The fix is the table in R5, applied by a human who read the failure.
- **It cannot see flakes that need a specific environment.** A test that only flakes on a loaded CI runner, on a specific timezone, or at month end will pass 10 local runs and fail on the one night it matters. The hunt is a screen, not a proof.
- **It does not know your runner.** The script runs pytest. If your suite is Jest, Go test, or RSpec, the procedure is the same -- run N times, count per-test outcomes, isolate the suspects -- but the script is not your runner. Port the counting, not the tool.
- **A green hunt does not bless a red test.** If a test failed in CI and passes 10 hunt runs, the hunt says the flake rate is low, not that the CI failure was meaningless. Read the CI failure first; the hunt is the second opinion, not the first.

## Tests

```bash
python3 tests/run_skill_tests.py
```

End-to-end tests on a deterministic fixture (a test that fails on alternate runs via a counter file, so the detector's own tests are not flaky), a clean-suite hunt that passes, the isolate command, the classifier on both families, the quarantine text, and a bad path as a usage error. The probabilistic fixture in `examples/fixture/` is the measurement corpus from the blog post, not a test fixture: its rates are measured over 100 runs in `flake-rates.json`, shipped with the post.
