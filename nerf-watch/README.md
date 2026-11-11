# Nerf-watch

A frozen regression suite for your coding agent. Eight small tasks, one
headless run each, deterministic checks, and a log you can compare week
to week — so when a model "feels nerfed", you have a number instead of
a vibe.

Built for the blog post ["Is Opus 5.5 nerfed? The trackers say no. One
user's logs say yes. Measure it yourself."](https://sanoj.dev/blog/is-opus-5-5-nerfed/)
(November 11, 2026), about the Opus 5.5 nerf debate: the public
trackers show no drop, one user's 6,638-answer log shows corrections
jumping from 5.2% to 25.4% after October 19, and both can be true.

## Install

Copy this folder into `~/.claude/skills/` (every project) or
`<project>/.claude/skills/` (one project):

```bash
cp -r nerf-watch ~/.claude/skills/
```

Requires Python 3.10+ and Claude Code 2.1.302 or later. No packages.

Headless runs need `ANTHROPIC_API_KEY` set (or an `apiKeyHelper` in
settings) — a Claude subscription sign-in alone does not authenticate
a `--bare` run. See `SKILL.md` §2.

## Quick start

```bash
cd ~/.claude/skills/nerf-watch
python3 scripts/run_suite.py --model claude-opus-5-5 --effort medium
```

That runs the eight tasks and writes
`results/<date>-claude-opus-5-5-medium.json`. Do it once to set your
baseline, then weekly, or whenever the model feels off. Compare two
runs with:

```bash
python3 scripts/compare.py results/<older>.json results/<newer>.json
```

Two or more tasks flipping is worth investigating; one is noise. The
SKILL.md has the full checklist for reading a drop — check the CLI
version, the effort level, and whether any task changed before blaming
the model.

## What is in here

- `SKILL.md` — the skill: the three rules, how to run it, how to read
  a drop, and what it does not prove.
- `tasks/tasks.json` — the eight frozen tasks, their prompts, and
  their checks. Do not edit a task once it has a logged run.
- `tasks/fixtures/` — the starting files each task runs against.
- `scripts/run_suite.py` — the runner and scorer.
- `scripts/compare.py` — compare two runs.
- `scripts/stub_agent.py` — a fake `claude` for testing the harness
  without a live model.
- `references/effort-and-pinning.md` — effort defaults per model, how
  to pin model, effort, and CLI version, and how to check what a run
  actually used.
- `tests/` — the stub's canned solutions and the deliberately wrong
  answer used to prove the checks can fail.
- `examples/sample-results.json` — what a passing run's result file
  looks like.

## What was tested

The runner, scoring, and comparer were tested end to end with the stub
agent: 8/8 pass with correct solutions, 7/8 with one deliberately
wrong answer, and `compare.py` flags a two-task drop and treats a
one-task drop as noise. A live run against a real model was **not**
tested here — it needs Claude Code installed and authenticated with
an API key (see above). Your first live run is the baseline.

## Cost

Eight tasks, each capped at 10 turns and $2. On Opus 5.5 at medium
effort a full run should cost only a few cents of model time.

## License

MIT. Original work — the tasks, checks, and scripts are mine. The
motivation (the #105112 numbers, the LiveNerf panel) is credited in
the blog post linked above.
