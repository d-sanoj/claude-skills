---
name: log-triage
description: Find the real cause of a failing build, test run, or CI job before fixing anything. Use when a build or test run fails and there is a log, when an agent is about to "fix" a failure it has not identified, when a pasted log is hundreds of lines long, or when the same failure keeps coming back. Reads the log first-error-first instead of bottom-up, treats a traceback as one unit, ignores summary lines that name no cause, and classifies the failure as defect, config, or environment — with a script that does the mechanical part deterministically.
---

# Log-triage: the first error is the cause, the last line is the eulogy

A build fails. The log is 200 lines long. The agent scrolls to the bottom, reads the last line — `Process completed with exit code 1` — and starts "fixing" whatever it guesses. The actual cause is 40 lines up, in a sentence that does not contain the word "error".

This is not a hypothetical. I collected 10 broken builds from my own repos — four real CI logs and six reproductions of real failures — and scored four ways of reading them. Reading the last 20 lines named the cause in **1 of 10**. Grepping the first line containing "error" got **5 of 10**. Grepping the last one got **2 of 10**. The procedure in this skill got **10 of 10**. The full numbers and the logs are in the blog post ["Your agent fixes the wrong line of the log"](https://sanoj.dev/blog/first-error-not-the-last-line/) (November 21, 2026).

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/triage-log.py" build.log
```

Tools: Python 3.10+. No packages, no network, no model calls.

## The measurement behind it

Ten logs, 975 lines: four verbatim GitHub Actions logs and six reproductions (the real tool run on a real repo copy with a real defect). Ground truth is the root cause as established by the fix that actually resolved each failure. A method "names the cause" only if what it surfaces identifies both what broke and where.

| Way of reading | Correct |
|---|---|
| Last 20 lines | 1/10 |
| First line containing "error" | 5/10 |
| Last line containing "error" | 2/10 |
| **This skill's procedure** | **10/10** |

The script's classification guess (defect / config / environment) was right in 9 of 10 — the one miss was a bad import line it called config. Classification is a guess to verify, not a verdict. The measurement script and the corpus ship with the blog post.

## 1. Save the log, don't paste it

Never paste a whole log into the conversation. A 200-line log costs more context than the fix, and the model reads what you pasted, not what the run produced. Save it to a file first:

```bash
npm run build:dist > build.log 2>&1
# or: gh run view <id> --log > build.log
```

Then run the script on the file. If the log is from CI, download it — do not retype the last lines from memory.

## 2. Run the triage script, read the verdict

```bash
python3 scripts/triage-log.py build.log
```

```text
ROOT CAUSE: Chrome did not open a debugging port
STEP:       Build
COMMAND:    node scripts/build.js --dist
CLASS:      environment
NEXT:       rerun first: if it passes, it was the environment, not your change.
```

The verdict names four things: the cause line, the file:line, the failing command or step, and the class. Read the evidence block it prints — the lines around the cause — before believing it. The script is a mechanical first pass, not a replacement for reading.

## 3. The rules (what the script does, and what to do by hand)

**R1 — The first real error is the cause; everything after it is cascade.** Failures compound: one broken import fails every test, one missing file fails two checks, one bad version prints 25 lines of the same pattern. Fix the first one and rerun; most of the rest disappears. Never fix the last error first.

**R2 — A traceback is one unit; its cause is its last line.** `Traceback (most recent call last):` says nothing. The exception is at the bottom: `ModuleNotFoundError: No module named 'x'`, or pytest's `file:line: AssertionError`. Read a traceback bottom-up. The same applies to pytest's short tracebacks: the `E` line and the `file:line: Exception` line at the end are the cause, not the `def test_...` lines above them.

**R3 — Summaries are not causes.** `Found 2 errors.`, `Process completed with exit code 1.`, `npm error Usage: ...`, `A complete log of this run can be found in: ...` — these name nothing. They are the eulogy, not the diagnosis. The same goes for warning noise: `npm warn`, deprecation warnings, a passing test whose name contains the word "error", a fixture description that mentions a failure case. If a line does not say what broke and where, it is not the cause.

**R4 — If a step has no error line, the cause is the step's last substantive line.** Some failures never print the word "error". A Chrome that never opens a debugging port, a process killed by the runner, a hang that times out — the cause is the process's last words before it died, in the failing step, just above the exit-code line. Do not read the post-job cleanup lines after the exit; they belong to a different step.

**R5 — Collapse repeats, then count once.** Twenty-five lines of the same pattern are one failure, not twenty-five. The script reports the repeat count. If the same error repeats with different file names, it is one broken thing (a bad import, a bad version) failing everywhere it is used — fix the one thing.

**R6 — Name the failing command, then reproduce it locally before fixing.** The verdict's COMMAND line is the command to run. Run it yourself and watch it fail the same way. If it passes locally, the failure is a difference between the two environments — tool versions, environment variables, caches, file ordering, timezone — and changing code will not fix it. Investigate the difference first.

## 4. Classify before fixing

The script guesses one of three classes. Each one means a different next step:

- **defect** — the code is wrong: a failing assertion, a syntax error, a bad import, an undefined name. Reproduce locally, fix the smallest cause, rerun the same command.
- **config** — the setup is wrong: a missing file, a lockfile that disagrees with the manifest, a missing type-stub package, a bad version. Fix the config or dependency, then rerun. Do not touch the code.
- **environment** — the machine is wrong: Chrome never started, the network dropped, the disk filled, the registry refused. Rerun first. If it passes, it was the environment, not your change.

The classification is a keyword guess. Verify it the same way you verify the cause: reproduce, then look at what actually failed. The one miss in the measurement was a bad import the script called config — a typo is a defect, a missing package is config, and no keyword rule can tell them apart.

## 5. What to never do

- **Never fix the failure by deleting a test, skipping it, or marking it expected-to-fail.** That makes the log green and the bug permanent.
- **Never loosen a version constraint, a type check, or a lint rule to make a run pass** without saying what the constraint was protecting.
- **Never fix the last error.** If you have not identified the first one, you have not identified the cause.
- **Never declare a failure flaky from one log.** Flaky means "passes on rerun". One log cannot prove that — rerun it. If it passes, say so; if it fails the same way twice, it is not flaky.

## 6. What this does not do

- **One log cannot prove flakiness.** Rerun the same command; a failure that passes on rerun is environment or flake, a failure that repeats is a defect or config.
- **A truncated log may not contain the cause.** If the log starts mid-run or the script reports no error line, get the full log before guessing.
- **The script does not know your project's error formats.** It recognises pytest, mypy, ruff, npm, node, and GitHub Actions logs. A project-specific error format needs its own pattern — add it to the script's pattern lists, and add a test in `tests/`.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule: a Chrome-style log with no error word, a pytest traceback, a ruff summary that names nothing, an npm lockfile cascade that collapses to one line, and a log where the first "error" match is a line of source code.
