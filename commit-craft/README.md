# Commit-craft

Make your coding agent write commits like a senior engineer.

An agent treats a commit message as one more place to narrate the
session — a paragraph of what it tried, a list of everything it
touched, a co-author trailer, sometimes your own words quoted back at
you. The result is a log nobody can read: subjects that wrap twice,
bodies that retell the afternoon, and one giant commit holding the
change a future reader actually needs to understand. A line in
`CLAUDE.md` does not fix it — developers report agents dumping
"multi-paragraph comments of Claude speak everywhere" even with
"use conventional commit messages and keep it nice and tight" already
in their instructions. So this skill builds a gate instead: five rules
and a checker script that runs before the commit lands.

Built for the blog post ["I measured 132 of my agent's commits. The
bad ones carry 84% of the code."](https://sanoj.dev/blog/agent-commit-messages-measured/)
(November 19, 2026). The post measured the author's own history — 132
non-merge commits across five agent-assisted repos, November 5–18,
2026 — with this checker's rules: 25 fail at least one rule (19%),
107 are clean. The failures concentrate where they hurt most: failing commits touch a median of 11
files against 1 for clean commits, and carry 511 of 788 files (65%)
and 89,890 of 106,935 inserted lines (84%). The measurement script and results ship with the post.

Original work, built from the author's own repos and from public
complaints: a Hacker News comment (September 2026) in the "How to Write
with an LLM" thread — "The long-ass Claude commit messages & PR
descriptions suck" — and Eva Martin's ["I WILL HAVE YOU ULTRATHINK ON
WHAT A BAD CLAUDE YOU WERE"](https://hapax.fi/note-what-leaks.html)
(November 2026), which surveyed public GitHub commit messages and
found developers' angry words committed verbatim. The rules follow the
[Conventional Commits](https://www.conventionalcommits.org/) shape —
short imperative subject, body only for the "why" — without requiring
its exact format.

## Install

Copy this folder into `~/.claude/skills/` (every project) or
`<project>/.claude/skills/` (one project):

```bash
cp -r commit-craft ~/.claude/skills/
```

Requires Python 3.10+ and git. No packages, no network, no model calls.

## Quick start

1. Stage one logical change: `git add -p`, or `git add` the files for
   that concern only. Never `git add .`.
2. Write the message in a file — subject on line one, blank line, body
   only if the "why" needs it:

```
Blog: your agent's code needs checks, not rules
```

3. Run the checker on what is staged:

```bash
python3 scripts/check-commit.py --staged --message-file msg.txt
```

4. If it fails, rewrite the message or split the commit — then commit
   with the file: `git commit -F msg.txt`.

To check a commit that already landed:

```bash
python3 scripts/check-commit.py --ref HEAD
```

## The five rules

The rules are numbered to match the checker: R1 is the subject, R2
the body, R3 the trailer, R4 the size of the change, R5 the files in
it.

1. **R1 — Subject: imperative, at most 72 characters, no trailing period.**
   Says what changed and, where the words allow, why.
2. **R2 — Body: at most five lines, only the "why".** Never narrates the
   session, never lists files, never quotes the user.
3. **R3 — No tool credit.** No `Co-Authored-By`, no "Generated with", no
   robot emoji. The author is the human.
4. **R4 — One logical change per commit.** If the diff touches two
   concerns, it is two commits. The revert test: could someone revert
   this commit without losing an unrelated change?
5. **R5 — Read the diff and run the checker before committing.** Stage by
   concern, read `git diff --cached`, and never commit generated
   output, chat transcripts, or secrets.

See `SKILL.md` for the full rules, the workflow, and the exceptions
(initial imports, tracked generated files, reverts), and
`examples/before-after.md` for real rewrites from the measurement.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule, plus the real messages from the
measurement: the 92-character blog-post subject fails R1, its
47-character rewrite passes, the 62-file import fails R4, and the
147-file restructure warns on R4 — but still fails R5, because a
generated build stamp rode along with the move.
