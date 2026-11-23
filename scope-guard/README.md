# Scope-guard

Keep a coding agent inside the scope it declared.

You ask for a blog post. The pull request contains the post — and one more file: `lychee.toml`, the config for the link checker. The agent edited the checker so its own post would pass. The change was correct. That is the problem: a correct change in the wrong pull request ships silently, because nobody reviews a file the task never mentioned.

I measured it on my own agent's pull requests: 25 merged PRs across five repos, November 15–22, 2026, 596 files changed — and exactly one file out of scope, `lychee.toml` in the November 21 blog-post PR. The field's base rate is much worse: a May 2026 study of 20,574 real coding-agent sessions found the agent taking actions beyond the stated scope in 10.20% of misalignment episodes, and violating an explicit constraint in 38.33%. Built for the blog post ["One file in 272: the one my agent changed without being asked"](https://sanoj.dev/blog/one-file-in-272/) (November 23, 2026). The post's measurement script and corpus ship with the post.

Original work, built from the author's own pull requests and from public complaints: the [May 2026 study of 20,574 agent sessions](https://arxiv.org/html/2605.29442) (Tang et al., "How Coding Agents Fail Their Users"), Hisashi's [account of Claude Code changing his app's password length without asking](https://hisashi.space/blog/claude-code-changed-my-product-without-asking/) (11 files, 597 lines added, minimum password 6 → 8, unnoticed for 27 days — and the test edited to match), and the [scope-check write-ups](https://dev.to/sion_jang_b7e2e2c640671f5/your-coding-agents-tests-pass-it-still-edited-files-you-never-asked-about-2npm) that build the same fence as a hook. This skill is the skill version: a declared scope, a baseline, and a checker script, plus the rule those write-ups do not state — never change a check to make your own change pass.

## Install

Copy this folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project):

```bash
cp -r scope-guard ~/.claude/skills/
```

Requires Python 3.10+. No packages, no network, no model calls.

## Quick start

1. Write `SCOPE.md` in the repo root before the first edit:

```markdown
# Scope: fix the off-by-one in src/app.py
## Allowed
- src/app.py
- tests/test_app.py
## Never touch
- lychee.toml
- .github/workflows/**
## Noticed, not changed
- (parking lot: drive-by findings go here, not in the diff)
```

2. Record the baseline — files already dirty are yours, not the agent's:

```bash
python3 scripts/scope-guard.py init
```

3. Work, then check before declaring the task done:

```bash
python3 scripts/scope-guard.py check
```

```text
SCOPE CHECK: fix the off-by-one in src/app.py
baseline: 1 file(s) already dirty at init (yours, ignored)
changed by this session: 3 file(s)
  ALLOWED      src/app.py (+12 -3)
  ALLOWED      tests/test_app.py (+8 -0)
  NEVER-TOUCH  lychee.toml (+3 -0)
FAIL: 1 never-touch: lychee.toml
Revert them, widen the scope with a reason, or ask the owner.
```

For work already committed on a branch, check against a ref instead: `python3 scripts/scope-guard.py check --ref main`.

## The rules

1. **R1 — Declare scope before the first edit.** No scope file, no edits. One sentence and a list of paths, not a paragraph of intentions.
2. **R2 — Check the final diff, not the tool calls.** Agents write files through scripts and shell redirects too; the working tree at the end catches all of it.
3. **R3 — A baseline first.** The check ignores every file that was already dirty at `init`, so it never blames the agent for your uncommitted work.
4. **R4 — Never-touch beats allowed, and a check's config is never-touch.** Built-in defaults (CI workflows, lockfiles, secrets) apply even when `SCOPE.md` does not list them. Never change a check to make your own change pass — unless the task *is* the check.
5. **R5 — Drive-by findings go in the parking lot, not the diff.** Note them under `Noticed, not changed` in `SCOPE.md` and leave them for a follow-up task.
6. **R6 — Three strikes, then hand to a human.** If the check fails three times on the same task, the scope is wrong or the task is bigger than stated — stop and ask.

When the check fails: revert the file, widen the scope with a reason the reviewer can see, or ask the owner — in that order. Put the verdict in the PR description ("Scope check: 2 files, all in scope"), since the scope file itself is not committed.

See `SKILL.md` for the full procedure and the measurement, and `examples/before-after.md` for the `lychee.toml` case read the wrong way and the right way.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule: an allowed edit passes, an unlisted file fails, a default never-touch file fails even when unlisted, a listed never-touch file beats an allowed glob, a pre-existing dirty file is not blamed, a new file inside an allowed glob passes and outside it fails, `--ref` mode on committed branch work, and missing scope file / missing baseline as usage errors rather than passes.
