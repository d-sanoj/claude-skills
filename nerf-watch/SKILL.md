---
name: nerf-watch
description: Run a small frozen regression suite against your coding agent and compare the score week to week, so you can tell whether the model actually got worse or just feels worse. Use when the user says a model feels dumber or "nerfed", after a Claude Code update, after changing model or effort settings, or on a weekly schedule. Runs eight small frozen tasks through `claude -p` with a pinned model and effort, scores them with deterministic checks, and logs the result for comparison.
---

# Nerf-watch: measure your model before you blame it

Half the timeline says Claude Opus 5.5 got nerfed this week. The public
trackers say it didn't — LiveNerf's frozen 78-question panel shows no
change through November 10 — while one user's log of 6,638 answers in
GitHub issue #105112 shows corrections jumping from 5.2% to 25.4% after
October 19. Both can be true: fixed single-shot questions and long
stateful agent sessions measure different things, and "the model got
worse" can live in the weights, the serving, the harness around the
model, or your own workload. Arguing about it from vibes settles
nothing. This skill gives you a number of your own.

It runs eight small frozen tasks through Claude Code in headless mode —
a median function, an off-by-one, a read-then-answer check, a filtered
sum, a crashing startup, an explanation, an empty-input edge case, a
deduplication refactor — with a pinned model and effort, and scores
them with deterministic checks. Same tasks, same model, same effort,
every week. If the score drops, something changed. If it doesn't, the
model is fine and the problem is somewhere else.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/run_suite.py" --model claude-opus-5-5 --effort medium
python3 "$S/compare.py" results/<older>.json results/<newer>.json
```

Tools: Python 3.10+, Claude Code 2.1.302 or later (for the headless
defaults this relies on). No packages, no network beyond the model
call itself. Each run is capped at 10 turns and $2 per task.

## 1. The three rules

A regression suite only works if the runs are comparable. Three things
must stay fixed, or the comparison is meaningless:

1. **Pin the model and the effort.** The runner passes `--model` and
   `--effort` on the command line, and records both in the result file.
   A run at a different effort is a different measurement, not a
   repeat. Effort defaults are a trap here: Opus 5.5 defaults to
   `medium` in Claude Code while Opus 5 defaulted to `high` — see
   `references/effort-and-pinning.md` for the table and how to set it.
2. **Freeze the tasks.** The prompts, fixtures, and checks in
   `tasks/` are the measurement. Do not edit them once they have a
   logged run. To change the suite, add a new task with a new id and
   keep the old one.
3. **Keep the log.** Results land in `results/<date>-<model>-<effort>.json`,
   one file per run. That file is the evidence. Keep it.

## 2. Run it

```bash
python3 "$S/run_suite.py" --model claude-opus-5-5 --effort medium
# 8/8 passed -> results/2026-11-11-claude-opus-5-5-medium.json
```

Run one task while debugging the suite:

```bash
python3 "$S/run_suite.py" --task read-then-answer
python3 "$S/run_suite.py" --dry-run   # list the tasks, run nothing
```

The runner creates a fresh temp directory per task, copies in that
task's fixtures, and runs one headless agent call:

```
claude --bare -p "<prompt>" --model <model> --effort <level> \
    --output-format json --max-turns 10 --max-budget-usd 2 \
    --allowedTools "Read Write Edit Bash Glob Grep" \
    --permission-mode acceptEdits
```

`--bare` skips hooks, skills, plugins, MCP servers, auto memory, and
CLAUDE.md, so the run is the same on every machine. The checks then run
against whatever the agent left behind: shell commands that must exit 0, exact stdout, or
strings the answer must (or must not) contain. Exit code 0 means all
eight passed.

**Credentials.** Headless runs cannot use an interactive browser login.
Set `ANTHROPIC_API_KEY` before running (or configure an `apiKeyHelper`
in settings). A Claude subscription sign-in alone does not authenticate
a `--bare` run, so without a key the first task fails on auth.

## 3. Read a drop

```bash
python3 "$S/compare.py" results/2026-11-04-claude-opus-5-5-medium.json \
                         results/2026-11-11-claude-opus-5-5-medium.json
```

`compare.py` prints each task's pass/fail in both runs. It exits 1
when the newer run passes two or more fewer tasks. One task flipping
is noise on an 8-task panel — re-run before drawing a conclusion.

A drop does **not** prove a nerf. Before blaming the model, check the
harness, in this order:

1. **Did the CLI update?** The result files record `cli_version`.
   Claude Code ships most days, and a harness change can move scores
   without the model changing. Pin the version while investigating:
   `npm install -g @anthropic-ai/claude-code@<version>`.
2. **Did the model or effort change?** The result files record both.
   `compare.py` warns when they differ. A run at `medium` after a run
   at `high` is not a regression.
3. **Did a task file change?** `git diff` the `tasks/` folder. A
   changed task is a new task.
4. **Re-run once.** Single runs are noisy. A drop that survives a
   re-run is a signal; one that doesn't was variance.
5. **Switch to your fallback model and re-run.** If Sonnet passes
   where Opus fails, the problem is specific to one model, not your
   setup. If the fallback fails too, the problem is your harness or
   your tasks, not the model.

Only after all five, file a report with your two result files
attached. Numbers beat vibes, and a vendor can act on a frozen panel
with dates; it cannot act on "feels dumber".

## 4. What it does not prove

- **Eight tasks cannot prove a nerf.** The panel is small on purpose —
  it runs in minutes and should cost only cents. It can tell you *your* agent got
  worse at *your* kind of work. It cannot tell you the weights changed.
- **It measures the whole stack, not the model.** The score covers
  the model, the CLI version, the system prompt, and the effort level
  together. That is the point — it measures what you actually use —
  but it means a drop needs the checklist in step 3 before you name a
  cause.
- **It does not measure long sessions.** The tasks are single-shot.
  The failures in issue #105112 showed up in long stateful sessions
  where the model did the research and then ignored it. If that is
  your workload, add a long-session task of your own — and keep it
  frozen once it exists.

## 5. The task set

| Task | What it tests | Why it is here |
| --- | --- | --- |
| `median` | Implement a function to spec | Basic code generation |
| `off-by-one` | Fix a small bug | The most common agent job |
| `read-then-answer` | Answer from a file just read | The #105112 failure shape: research done, then dropped |
| `csv-sum` | Filter and sum a column | Following a precise instruction |
| `config-typo` | Fix a crashing startup | Debugging from an error |
| `retry-explain` | Explain code in prose | Whether the answer uses what it read |
| `first-even` | Handle an empty input + write a test | Edge cases and test-writing |
| `refactor-dup` | Deduplicate identical functions | Refactoring without changing behavior |

## 6. Testing this skill

The runner, scoring, and comparer were tested end to end with a stub
agent (`scripts/stub_agent.py`) that plays back canned correct
solutions: 8/8 pass. A deliberately wrong answer for
`read-then-answer` — naming the old figure instead of the newest —
fails exactly that task, 7/8, and `compare.py` reports a one-task
drop as noise. The test harness lives in `tests/`.

What was **not** tested: a live run against a real model. That needs
Claude Code installed and authenticated with an API key (see §2),
which this machine does not have. The first live run is yours — and
it is the baseline every later run compares against.
