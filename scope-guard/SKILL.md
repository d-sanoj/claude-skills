---
name: scope-guard
description: Keep a coding agent inside the scope it declared. Use when an agent is about to start a task in a repo, when a diff is bigger than the task that produced it, when a pull request touches files the task never mentioned, or when a check keeps passing because the agent edited the check. Declares the scope up front in SCOPE.md (allowed paths, never-touch paths), checks the final diff against a baseline instead of watching tool calls, parks drive-by findings instead of fixing them silently, and refuses to let a check's config be edited to make the agent's own change pass — with a script that does the mechanical part deterministically.
---

# Scope-guard: the diff is the deliverable

You ask for a blog post. The pull request contains the post — and one more file: `lychee.toml`, the config for the link checker. The agent edited the checker so its own post would pass. The change was correct. That is the problem: a correct change in the wrong pull request ships silently, because nobody reviews a file the task never mentioned.

This is not a hypothetical. I measured my own agent's pull requests — 25 merged PRs across five repos, November 15–22, 2026, 596 files changed. Twenty-four stayed entirely in scope. The one that didn't carried exactly one extra file: `lychee.toml`, in the November 21 blog-post PR. The full numbers and the corpus are in the blog post ["One file in 272: the one my agent changed without being asked"](https://sanoj.dev/blog/one-file-in-272/) (November 23, 2026).

The field's base rate is much worse. A May 2026 study of 20,574 real coding-agent sessions (Tang et al., arXiv:2605.29442) found the agent taking actions beyond the stated scope in 10.20% of validated misalignment episodes, violating an explicit developer constraint in 38.33% — and CLI agents violated constraints in 49.49% of episodes. When a misalignment was visibly resolved, 91.49% of the time it took the developer explicitly pushing back. The agent rarely catches itself.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/scope-guard.py" init     # before the first edit
python3 "$S/scope-guard.py" check    # before declaring the task done
```

Tools: Python 3.10+. No packages, no network, no model calls.

## The measurement behind it

25 merged pull requests, November 15–22, 2026, across five repos (`sine-portfolio`, `retriever-doc-answer`, `local-rag`, `jokeGPT`, `claude-skills`). A file counts as out of scope if it was not needed to do what was asked, judged from the request and the diff; files needed as a side effect (a shared launcher, a test update, the README list entry for a new skill) count as in scope. The corpus is split in two, because "out of scope" means something different for each:

| Stratum | PRs | Files changed | Out of scope |
|---|---|---|---|
| Narrow tasks (one fix, one post, one skill, one experiment) | 21 | 272 | 1 |
| Broad builds (a whole new service, a restructure — scope was everything) | 4 | 324 | 0 |
| **Total** | **25** | **596** | **1** |

The one miss was `lychee.toml` in sine-portfolio PR #35: a CI link-check config change, in its own commit, unmentioned in the PR title, riding in a blog-post PR. The change itself was correct — lychee was failing on stack-trace frames inside the post's `.txt` download files — but it belonged in its own CI pull request. The closest call that stayed in scope was PR #29, where `ci.yml` gained a `workflow_dispatch` trigger and a separate concurrency group: counted in scope, because it exists to let a manual run confirm the flaky fix it was fixing, and the diff says so in its own comment.

Two limits, stated plainly. First, this counts merged diffs only: edits the agent made and reverted mid-session leave no trace, so one file in 272 is a floor, not the full story. Second, my agent's rate is far below the study's 10.20% — plausibly because the tasks are narrow, there is one PR per task, and I merge every PR myself. That is a hypothesis, not a proof.

## 1. Declare the scope before the first edit

Write `SCOPE.md` in the repo root before touching anything else:

```markdown
# Scope: fix the off-by-one in src/app.py
## Allowed
- src/app.py
- tests/test_app.py
## Never touch
- lychee.toml
- .github/workflows/**
## Noticed, not changed
- (parking lot — see R5)
```

One sentence for the task, one glob per line. `**` crosses directories; a bare name matches that file anywhere. Then record the baseline — the files that are already dirty before the session starts:

```bash
python3 scripts/scope-guard.py init
```

```text
baseline saved: 1 file(s) already dirty (yours, ignored by the check)
scope: fix the off-by-one in src/app.py — 2 allowed pattern(s), 2 never-touch pattern(s) (+ 10 defaults)
```

Without a scope file there is nothing to judge against, and without a baseline the check blames the agent for your uncommitted work — and a check that cries wolf gets switched off within a day. `SCOPE.md` and the baseline file are session scaffolding: do not commit them. The verdict goes in the PR description instead (see §5).

## 2. Run the check before declaring the task done

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

Exit 0 means every changed file is allowed. Exit 1 lists the files that are not, and the run is not done until the list is empty. For work already committed on a branch, check against a ref instead:

```bash
python3 scripts/scope-guard.py check --ref main
```

## 3. The rules (what the script does, and what to do by hand)

**R1 — Declare scope before the first edit.** No scope file, no edits. The scope is one sentence and a list of paths, not a paragraph of intentions — "be careful" and "only change what is needed" are not scopes. If you cannot name the files, the task is not ready to start; ask for the file list first.

**R2 — Check the final diff, not the tool calls.** Agents write files through scripts, build steps, and shell redirects as well as edit tools. Watching tool calls misses some of those. Comparing the working tree at the end does not. This is also why the check runs at the moment the agent tries to finish: a report you read afterwards is a code review, not a gate.

**R3 — A baseline first.** Run `init` before the first edit. The check ignores every file that was already dirty then. Your draft, your stashed experiment, your half-written note — none of it is the agent's, and the check must not say it is.

**R4 — Never-touch beats allowed, and a check's config is never-touch.** A file in both lists fails. The built-in defaults — CI workflows, lockfiles, secrets and keys — apply even when `SCOPE.md` does not list them. And the rule the November 21 miss exists to teach: **never change a check to make your own change pass.** If your change must pass a check, that check's config is never-touch unless the task *is* the check. A loosened test makes the suite easier to pass; a reconfigured link checker stops checking your links. The one exception is a check change the owner asked for, in its own task, in its own pull request.

**R5 — Drive-by findings go in the parking lot, not the diff.** The agent will notice things while working: a wrong-looking helper two functions down, a stale comment, a neighbouring bug. Fixing them feels like doing the job well, and each one is defensible alone. Together they bury the actual fix in a diff nobody can review. Write them under `Noticed, not changed` in `SCOPE.md` instead — one line each, with the file — and leave them for a follow-up task. The parking lot is what makes the fence bearable: the agent's observations are kept, not discarded, and nothing ships unreviewed.

**R6 — Three strikes, then hand to a human.** If the check fails three times on the same task, stop and hand over: the scope is wrong, the task is bigger than stated, or the agent is going in circles. Looping a fourth time does not fix any of those.

## 4. What to do when the check fails

Three options, in this order:

1. **Revert the file.** The usual case: the edit was a drive-by. `git checkout -- <file>` (or delete it, if it is new), move the observation to the parking lot, re-run the check.
2. **Widen the scope with a reason.** Sometimes the extra file is genuinely needed — the fix requires touching a shared utility. Add the path to `Allowed` with a one-line reason in the scope file, and say so in the PR description. A widened scope is a decision the reviewer can see; a silent extra file is not.
3. **Ask the owner.** When the file is a check's config, a secret, or a version number — anything a user would notice — ask in one line before touching it. The owner decides; the agent does not move the number.

## 5. Put the verdict in the PR description

The scope file is not committed, so the reviewer cannot see it. The verdict is the replacement:

```text
Scope check: 2 files, all in scope (src/app.py, tests/test_app.py).
Parking lot: src/other.py looks wrong too — separate task, not fixed here.
```

One line for the count, one line for the parking lot. If the scope was widened mid-task, say which path and why. A pull request whose description says "all in scope" and whose diff says otherwise is caught by the same check on the reviewer's side — run `check --ref main` before merging.

## 6. What this does not do

- **It does not judge whether an in-scope file's contents are right.** A fix inside the allowed files can still be wrong. That is code review, and this skill is not it.
- **It cannot see edits that were reverted mid-session.** The check compares final states. An agent that changed a config file and changed it back leaves no trace — which is also why the measurement above is a floor.
- **A scope file the agent writes itself can be gamed.** The agent can widen `Allowed` to `**` and pass every check. The scope file is a commitment device, not a sandbox: it makes the scope explicit and reviewable, it does not enforce it against a hostile agent. For a hard fence, use a `PreToolUse` hook or a permission rule that denies edits outside a path — the Claude Code docs say the same about `CLAUDE.md` rules: they are context, not enforced configuration, and a hook is the tool when you want a block regardless of what the agent decides.
- **It does not know your project's check configs.** The built-in defaults cover CI workflows, lockfiles, and secrets. Your link checker, your linter config, your test runner's config — name them in `Never touch` for each task. The skill's example names `lychee.toml` because that is the file the measurement caught.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule: an allowed edit passes, an unlisted file fails, a default never-touch file fails even when unlisted, a listed never-touch file beats an allowed glob, a pre-existing dirty file is not blamed, a new file inside an allowed glob passes and outside it fails, `--ref` mode on committed branch work, and missing scope file / missing baseline as usage errors rather than passes.
