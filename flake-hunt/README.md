# Flake-hunt

Find the flaky test before it eats your morning.

Thursday, 16:40. The build goes red on an integration test. Nobody opens the stack trace. Someone clicks retry, the second run comes back green, the PR merges. The failure was real, and it shipped — because the retry button cannot tell a test that is lying from a test that is right.

I measured it on a fixture suite of 9 tests with 4 deliberate flakes: a single run caught 2 of the 4; a 10-run hunt caught all 4. Over 100 runs the flakes failed 56, 29, 27, and 100 times out of 100, while the stable tests failed 0 times — and 12 real tests from my local-rag repo ran 20 times each with 0 failures, so the method does not cry wolf. The field's numbers are worse than the fixture: at Google, about 1.5% of test runs reported a flaky result and about 84% of pass-to-fail transitions involved a flaky test (Micco, 2016), and Luo et al. (FSE 2014) found async wait behind 45% of flaky-test fixes, concurrency 20%, test order dependency 12%. Built for the blog post ["The test that passes until it doesn't"](https://sanoj.dev/blog/the-test-that-passes-until-it-doesnt/) (November 25, 2026). The post's measurement script and rates ship with the post.

Original work, built from the author's own fixture measurement and from the literature: Martin Fowler's ["Eradicating Non-Determinism in Tests"](https://martinfowler.com/articles/nonDeterminism.html) (2011) for the quarantine rule, John Micco's ["Flaky Tests at Google and How We Mitigate Them"](https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html) (2016) for the scale, and Luo, Hariri, Eloussi and Marinov's ["An Empirical Analysis of Flaky Tests"](https://huang.isis.vanderbilt.edu/cs8395/paper/flakytest.pdf) (FSE 2014) for the causes and the fix-effectiveness numbers. The procedure here turns that research into a script that does the mechanical part deterministically.

## Install

Copy this folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project):

```bash
cp -r flake-hunt ~/.claude/skills/
```

Requires Python 3.10+ and pytest. No packages, no network, no model calls.

## Quick start

1. Hunt — run the suite 10 times and name every test that changed its answer:

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

Exit 0 means no test changed its answer; exit 1 means at least one did. The full report is in `flake-hunt-out/flake-report.md` and `.json`.

2. Isolate a suspect alone, to separate the two families (from the fixture directory):

```bash
python3 ../../scripts/flake-hunt.py isolate tests/test_flaky.py::test_async_result_ready --runs 5
```

A test that fails alone is time, random, or async. A test that passes alone but fails in the suite is order or shared state.

3. Quarantine what you found — the script prints the entry, you paste it in and file the ticket:

```bash
python3 scripts/flake-hunt.py quarantine tests/test_x.py::test_y
```

## The rules

1. **R1 — A rerun that passes is evidence, not a fix.** A test that fails 10% of the time passes a single run 90% of the time. Never merge on a green rerun of a red test without a hunt.
2. **R2 — Name the flake before fixing it.** Hunt, isolate, classify — in that order. Lengthening a sleep does not fix a flake: in Luo et al.'s study, 0 of 20 sleep fixes removed the flakiness; 23 of 42 waitFor fixes did.
3. **R3 — Fix the test, not the code, unless the failure is real.** Most flakes are bugs in the test. But 24% of flaky-test fixes in the study changed the code under test, and 94% of those fixed a real bug — so read the failure before deciding which side is wrong.
4. **R4 — Quarantine is a waiting room with an exit.** A confirmed flaky test leaves the merge-blocking suite the same day, into a quarantined suite that still runs, with a ticket, an owner, and a deadline. Cap the quarantine (e.g. 8 tests) and fix them within a week.
5. **R5 — Fix by cause, not by symptom.** Async wait: wait for the condition, not a number of seconds. Wall clock: inject the clock. Unseeded random: seed it and log the seed. Order/shared state: fresh fixture per test. Concurrency: fix the race. Remote service: use a test double.
6. **R6 — Three hunts, then hand to a human.** If the same test is still flaky after three fix attempts, the cause is not in the list above — stop and ask.

A 10-run hunt misses a 1% flake 90% of the time, so a clean hunt means "no flake above a certain rate", not "no flakes". For a suite you are about to trust with a release, run 20.

See `SKILL.md` for the full procedure and the measurement, `examples/fixture/` for the 9-test suite the measurement ran on, and `examples/before-after.md` for the Thursday 16:40 build read the wrong way and the right way.

## Tests

```bash
python3 tests/run_skill_tests.py
```

End-to-end tests on a deterministic fixture (a test that fails on alternate runs via a counter file, so the detector's own tests are not flaky), a clean-suite hunt, the isolate command, the classifier on both families, the quarantine text, and a bad path as a usage error. The probabilistic fixture in `examples/fixture/` is the measurement corpus from the blog post; its rates are measured over 100 runs and ship with the post.
