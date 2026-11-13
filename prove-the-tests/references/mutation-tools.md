# Mutation testing tools

The built-in `scripts/mutant_check.py` uses hand-written mutants:
you list the breaks in a JSON file and it applies them one at a time.
That is enough for a diff-sized check, and it has one advantage over
real tools — every mutant is a change you chose, so every survivor
is a specific blind spot you already understand. Its limit is scale:
a real tool generates hundreds of mutants from the code itself, and
hand-writing that many is not worth it.

Graduate to a real tool when the hand-written list stops being
enough — a module with more than a few dozen lines, or a check you
want in CI. The established tools, by language:

| Language | Tool | Notes |
| --- | --- | --- |
| JavaScript / TypeScript | **Stryker** (stryker-mutator.io) | The standard. Runners for Jest, Vitest, Mocha, Karma, Jasmine, Tap, and others. Supports a `break` threshold in CI (`--threshold` / `mutation score >= X` in the config) so a PR fails below it. |
| Python | **mutmut** | Small, focused, pytest/unittest friendly. `mutmut run --paths-to-mutate src/`. |
| Python | **cosmic-ray** | More operators, slower, more thorough. Good for a nightly run rather than every commit. |
| Java / Kotlin | **PIT** (pitest.org) | The standard for the JVM. Gradle and Maven plugins, HTML reports, CI-friendly thresholds. |
| Rust | **cargo-mutants** | Works from the test suite you already have. The HN thread in October 2026 used it with cargo-test-prune to find removable tests. |
| .NET | **Stryker.NET** | Same family as StrykerJS. |

## How to use one well

- **Scope it to the diff.** Full-codebase mutation runs take
  minutes to hours. Run it on the files the PR touched, in CI, with
  a threshold (commonly 80%) rather than a demand for 100%.
- **Expect equivalent mutants.** A real tool generates changes that
  do not alter behaviour. Stryker and PIT let you mark them and move
  on; do not chase them.
- **Read the survivors, not the score.** The score is a gate. The
  survivor list is the work: each one names a line and a kind of
  mistake your tests ignore.
- **Mutation testing checks detection, not intent.** It answers
  "does this test detect a change?" It does not answer "is the
  requirement right?" — that is still Rule 1's job.

## The industrial version

Meta's Catching JiTTests (Engineering at Meta, 29 October 2026)
generate tests designed to fail, targeted at risky diffs, and
surface the failures to engineers for a verdict. In the first half
of 2026 the system helped catch 74 serious privacy bugs at the diff
stage, with engineers reporting a 60% true-positive rate. The idea
is the same as this skill's — a test earns trust by failing — run
at a scale no hand-written mutant list can reach.
