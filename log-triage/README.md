# Log-triage

Find the real cause of a failing build before fixing anything.

A build fails, the log is 200 lines long, and the agent scrolls to the bottom, reads `Process completed with exit code 1`, and starts "fixing" whatever it guesses. The actual cause is 40 lines up, in a sentence that does not contain the word "error".

I measured it on 10 broken builds from my own repos: reading the last 20 lines named the cause in 1 of 10, grepping the first "error" in 5 of 10, grepping the last in 2 of 10. This skill's procedure — first real error, traceback as one unit, summaries are not causes — got 10 of 10. Built for the blog post ["Your agent fixes the wrong line of the log"](https://sanoj.dev/blog/first-error-not-the-last-line/) (November 21, 2026). The post's measurement script and the 10-log corpus ship with the post.

Original work, built from the author's own CI logs and from public complaints: the [Vibe Coding How-To guide on massive logs](https://www.vibecodinghowto.com/article/qa-context-blowup) ("If you cannot quickly find the failure yourself, you have a bigger problem than context size — you don't know what you're looking for, and the model won't either") and the [failing-build prompt](https://www.prompthackers.co/prompts/ci-failure-fixer) that tells the agent to quote "the first real error, not the last line printed". The procedure here turns that advice into a script that does the mechanical part deterministically.

## Install

Copy this folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project):

```bash
cp -r log-triage ~/.claude/skills/
```

Requires Python 3.10+. No packages, no network, no model calls.

## Quick start

1. Save the failing log to a file — never paste hundreds of lines into the conversation:

```bash
npm run build:dist > build.log 2>&1
# or: gh run view <id> --log > build.log
```

2. Run the triage script:

```bash
python3 scripts/triage-log.py build.log
```

3. Read the verdict — cause, file:line, failing command, class — and the evidence block. Reproduce the failing command locally before fixing anything.

## The rules

1. **R1 — The first real error is the cause; everything after it is cascade.** Fix the first one and rerun; most of the rest disappears.
2. **R2 — A traceback is one unit; its cause is its last line.** `Traceback (most recent call last):` says nothing. The exception is at the bottom.
3. **R3 — Summaries are not causes.** `Found 2 errors.`, `Process completed with exit code 1.`, `npm error Usage: ...` name nothing.
4. **R4 — If a step has no error line, the cause is the step's last substantive line** — the process's last words before it died.
5. **R5 — Collapse repeats, then count once.** Twenty-five lines of the same pattern are one failure.
6. **R6 — Name the failing command, then reproduce it locally before fixing.** If it passes locally, the failure is an environment difference, not your code.

Classify before fixing: **defect** (fix the code), **config** (fix the setup, don't touch the code), **environment** (rerun first). The classification is a guess — verify it by reproducing. Never fix a failure by deleting or skipping a test, and never declare a failure flaky from one log.

See `SKILL.md` for the full procedure and the measurement, and `examples/before-after.md` for the Chrome log read the wrong way and the right way.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule: a Chrome-style log with no error word, a pytest traceback, a ruff summary that names nothing, an npm lockfile cascade that collapses to one line, and a log where the first "error" match is a line of source code.
