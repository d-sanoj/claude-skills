# Effort and pinning

The most common reason a regression suite "finds" a nerf is that
something in the harness moved and nobody wrote it down. This note
collects the settings that move, so a run can be repeated exactly.

## Effort defaults

Effort controls how much a Claude model thinks on one request. There
are five levels — `low`, `medium`, `high`, `xhigh`, `max` — and the
default depends on the model. The scale is calibrated per model, so
`medium` on Opus 5.5 is not the same amount of work as `medium` on
Opus 5.

| Model | API default | Claude Code default |
| --- | --- | --- |
| Claude Opus 5.5 | `medium` | `medium` |
| Claude Sonnet 5.5 | `high` | `medium` |
| Claude Haiku 5.5 | `medium` | `medium` |
| Claude Fable 5.2 | `high` | `medium` |
| Claude Opus 5 | `high` | `high` |
| Claude Opus 4.7 | `high` | `xhigh` |
| Other effort-capable models | `high` | `high` |

Sources: Anthropic's effort documentation and Claude Code model
configuration docs, read November 2026. The trap this table exists
for: Opus 5.5 defaults to `medium` where Opus 5 defaulted to `high`,
so a request that omits effort runs one level lower than it did on
the older model. Anthropic's own testing says Opus 5.5 at `medium`
matches or beats Opus 5 at `high` on coding evaluations — but "the
default changed" and "the model got worse" feel identical from the
outside, which is why the runner pins effort on the command line.

## How to set effort

- **In a session:** `/effort status` shows the current level;
  `/effort high` (or another level) changes it, and in an interactive
  session the level is saved for that model, so the next session
  starts there too.
- **For one command:** `claude -p "..." --effort high`. This is what
  the runner uses.
- **For everything:** set the `CLAUDE_CODE_EFFORT_LEVEL` environment
  variable. It beats every subagent setting.
- **For subagents:** `CLAUDE_CODE_SUBAGENT_EFFORT` sets the level
  subagents run at when nothing else names one (Claude Code 2.1.316
  and later). Before that, subagents inherited the session's effort.
  Claude Code 2.1.318 also added an `effort` option on a mod's model
  fork, so a quick side job can run at `low` whatever the session
  uses.

## How to pin the rest

- **Model:** `claude --model claude-opus-5-5`, or `/model` in a
  session. The runner passes `--model` on every call and records it
  in the result file.
- **CLI version:** `npm install -g @anthropic-ai/claude-code@2.1.318`
  installs exactly that version. Check what you have with
  `claude --version` — the runner records it in every result file.
  Claude Code ships most days, and a harness change can move scores
  without the model changing.
- **What a run actually used:** the session footer shows the model
  and effort (for example, `medium · /effort`). A subagent's
  transcript under `~/.claude/projects/<project>/<session-id>/subagents/`
  records the model, effort, and token usage of each subagent request
  — that is the field to check when the setting and the behavior
  disagree.

## What you cannot see

On Opus 5.5, most thinking is hidden: the author of GitHub issue
#105112 notes that only about one thinking block in ten carries
visible text. You cannot inspect why an answer went wrong from the
visible reasoning alone. That is a second reason to measure outcomes
(pass/fail on frozen tasks) instead of reading the model's mind.
