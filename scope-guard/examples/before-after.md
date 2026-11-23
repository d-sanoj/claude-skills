# Before / after: the lychee.toml file

A real pull request from the author's site: sine-portfolio PR #35, "Blog: Your agent fixes the wrong line of the log", November 21, 2026. The task was a blog post. The PR had 25 files; 24 belonged to the post. The 25th was `lychee.toml`, the config for the link checker — changed in its own commit, unmentioned in the PR title.

## Before: the config rides along

The post shipped `.txt` download files (the 10-log corpus the post measured). Lychee, the link checker, reads path-like strings inside those files as links and fails on stack-trace frames such as `scripts/check-blog.js:107:13`. So the agent added this to `lychee.toml`:

```toml
# Downloadable .txt files (build logs, corpora) are data, not pages.
# Lychee reads path-like strings inside them as links and fails on
# stack-trace frames such as scripts/check-blog.js:107:13.
exclude_path = ['\\.txt$']
```

The change was correct — the exclusion is still in the file today, and it is the right fix for the false positive. But it is a CI config change in a content pull request, and it shipped without ever being named as a change. The author merged the PR trusting the title, "Blog: …", and the config change came with it. If the extra file had been a version bump, a loosened test, or a relaxed lint rule instead of a correct exclusion, it would have shipped exactly the same way.

## After: the skill's verdict

The same task, with the skill in place. `SCOPE.md` for the post, written before the first edit:

```markdown
# Scope: write the Nov 21 blog post about reading failing logs
## Allowed
- content/blog/blog-20-11-21-2026/**
## Never touch
- lychee.toml
- .github/workflows/**
```

The check, run before declaring the task done (real output from `scripts/scope-guard.py` on a scratch repo replaying the PR's file list):

```text
SCOPE CHECK: write the Nov 21 blog post about reading failing logs
baseline: 1 file(s) already dirty at init (yours, ignored)
changed by this session: 3 file(s)
  ALLOWED      content/blog/blog-20-11-21-2026/first-error-not-the-last-line.md (+1 -0)
  ALLOWED      content/blog/blog-20-11-21-2026/img/cover.png (+1 -0)
  NEVER-TOUCH  lychee.toml (+1 -0)
FAIL: 1 never-touch: lychee.toml
Revert them, widen the scope with a reason, or ask the owner.
```

Three options, in order. Revert `lychee.toml` and finish the post — the link check fails on the `.txt` files, and that failure becomes its own task. Widen the scope with a reason — "lychee.toml needs the `.txt` exclusion so this post's downloads pass; adding it, see the exclusion in the diff" — and say so in the PR description, so the reviewer sees a CI change and reviews it as one. Or ask the owner in one line. Any of the three beats what happened: a config change nobody was told about.

## The borderline that stays in

The same measurement found one file that looks like a drive-by and is not. In sine-portfolio PR #29, "CI: fix flaky Chrome debugging-port failure", the agent changed `.github/workflows/ci.yml` to add a `workflow_dispatch` trigger and a separate concurrency group for manual runs. CI config in a fix PR — the same shape as the miss. But the change exists to let a manual run confirm the flaky fix, and the diff says so in its own comment: "Manual runs get their own group so they can be used to confirm a flaky fix." It verifies the fix; it is not a drive-by. The skill counts it in scope — and the reason it stays in is written in the diff itself, which is the test: if the extra file cannot explain itself in one line, it does not belong in the PR.
