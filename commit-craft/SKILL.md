---
name: commit-craft
description: Make your coding agent write commits like a senior engineer. Use when an agent writes commit messages, before committing agent-authored work, when a log is full of multi-paragraph "Claude speak", when one commit mixes several changes, or before merging an agent-authored pull request. Enforces one logical change per commit, a subject under 72 characters, a body under five lines, no tool credit, and no files the author did not mean to commit — with a checker script that gates the commit instead of trusting a line in CLAUDE.md.
---

# Commit-craft: your agent's commit messages are the public record

A commit message is signed with your name and stored in a public
history. An agent treats it as one more place to narrate the session —
a paragraph of what it tried, a list of everything it touched, a
co-author trailer, sometimes your own words quoted back at you. The
result is a log nobody can read: subjects that wrap twice, bodies that
retell the afternoon, and one giant commit holding the change a future
reader actually needs to understand.

This is not a hypothetical. A Hacker News comment from September 2026
puts it flatly: "The long-ass Claude commit messages & PR descriptions
suck. But they are 100% better than 'fix'." Another comment in the same
thread is from a developer who already has "use conventional commit
messages and keep it nice and tight" in their `claude.md`, reporting
that the agent "still dumps multi-paragraph comments of Claude speak
everywhere". Eva Martin's November 2026 survey
of public GitHub commit messages found "Stupid claude" filling a page
of commit search, developers' angry words committed verbatim, and 10%
of 195 commit messages addressing the tool as "you". The instruction
file does not work. One `CLAUDE.md` in her survey puts it best:
"DOCUMENTATION IS NOT ENFORCEMENT — BUILD THE GATE."

This skill is the gate: five rules, a checker that runs before the
commit lands, and a split workflow for the commit that is really several.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/check-commit.py" --staged --message-file msg.txt
```

Tools: Python 3.10+, git. No packages, no network, no model calls.

## The measurement behind it

I ran the checker over 132 non-merge commits from my own five
agent-assisted repos (November 5–18, 2026): 25 fail at least one rule
(19%), 107 are clean. The failures are not spread evenly — they
concentrate exactly where they hurt most. Failing commits touch a
median of 11 files against 1 for clean commits, and carry 511 of 788
files (65%) and 89,890 of 106,935 inserted lines (84%). The log reads
fine until the commit that matters, and that is the one nobody can
review. Full numbers and the script that produced them are in the blog post
["I measured 132 of my agent's commits. The bad ones carry 84% of the
code."](https://sanoj.dev/blog/agent-commit-messages-measured/)
(November 19, 2026).

## 1. The five rules

The rules are numbered to match the checker: R1 is the subject, R2
the body, R3 the trailer, R4 the size of the change, R5 the files in
it.

**R1 — the subject fits on one line: imperative, at most 72
characters, no trailing period.** It says what changed and, where the
words allow, why. "Add blog post: Your agent's code looks nothing like
yours. Stop writing rules. Write checks." is 92 characters — the whole
headline pasted as a subject. The rewrite is "Blog: your agent's code
needs checks, not rules" (47). Match the repo's existing prefix
convention (`Blog:`, `Fix:`, `Skill:`) instead of inventing a new one
per commit. A subject that needs a second line is a subject that needs
editing, not wrapping.

**R2 — the body is at most five lines, and only the "why".** The
body explains what the subject cannot: the reason, the trade-off, the
thing a reader would otherwise misunderstand. It never narrates the
session ("I tried X, then Y"), never lists every file touched (the
diff already does that), and never quotes the user. What you typed in
what felt like a private exchange ends up quoted in a committed file —
agents quote verbatim because recording what they were told shows they
were asked. Write the reason in your own words, once.

**R3 — no tool credit, no co-author trailer.** The author is the
human. No `Co-Authored-By: Claude`, no "Generated with", no robot
emoji, no "as requested" framing. The commit is signed with your name;
the record should read as yours. This is also a privacy rule: a
trailer advertises which tool wrote the code, and a quoted instruction
can leak what you were working on.

**R4 — one logical change per commit.** A commit is one idea: one
fix, one feature, one move. If the diff touches two concerns, it is
two commits. "Add CI pipeline, example data, and Streamlit GUI" was a
real commit of mine — 25 files, 13-line body — and it is four commits
(see `examples/before-after.md`). The test is the revert test: could
someone revert this commit without losing an unrelated change? If not,
split it. Pure moves are the exception: a rename of 147 files with 204
insertions is one commit, and the checker warns on its file count
instead of failing it — say it is a move in the subject ("Move blog
posts into per-post folders") so the warning reads as intended.

**R5 — read the diff before you commit, and run the checker.**
Stage by concern (`git add -p`), read `git diff --cached` — every
file, not just the stat — and then run the checker. Never `git add .`:
chat transcripts (`.specstory/history/`, `.aider.chat.history.md`),
generated output (`dist/`, `data/generated/`), and pasted secrets ride
in on a bare `add .`. A November 2026 code search found 15,040
SpecStory chat-history files and 5,592 Aider history files sitting on
public default branches. If the checker fails, rewrite the message or
split the commit. Do not commit and fix it later — later never comes,
and the bad message is already public.

## 2. The workflow

1. Finish the change. Stage one concern: `git add -p`, or `git add`
   the files for that concern only.
2. Write the message in a file first — subject on line one, blank
   line, body if the "why" needs it. Never compose it in the `git
   commit -m` argument: a heredoc-length message is the tell that the
   body is an essay.
3. Run the checker on what is staged:

```bash
python3 scripts/check-commit.py --staged --message-file msg.txt
```

4. If it fails on R4 (too many files), split: `git reset`, stage the
   first concern, commit it, repeat. If it fails on R1 or R2, edit the
   message — shorter subject, fewer body lines — and re-run. If it
   fails on R5, unstage the file and check `.gitignore`.
5. Commit with the file: `git commit -F msg.txt`. The message file
   itself is never committed.

To check a commit that already landed, pass its ref:

```bash
python3 scripts/check-commit.py --ref HEAD
```

## 3. What the checker enforces, and what it cannot

The checker enforces R1 (subject length, no trailing period), R2 (body
lines), R3 (trailers and tool credit), R4 (file count, with the
rename-heavy warning), and R5 (generated and accidental paths). It
cannot judge whether the subject is imperative, whether the body
explains the "why", or whether two concerns are hiding in ten files —
that is the author's job, in step 2 and in the revert test. A PASS from
the checker means the commit is shaped right, not that it is a good
commit. Read the diff anyway.

## 4. When the rules bend

- **Initial import.** The first commit of a repo breaks R4 by
  definition. Say so in the subject ("Initial import: ...") and move on.
- **Generated code you ship.** If generated files are the change (a
  lockfile update, a build artifact the repo tracks), the subject says
  so, and R5 does not apply to the files the repo deliberately tracks.
  The checker flags `dist/` and `data/generated/` because those are
  almost never the change; add your repo's tracked generated paths to
  the script's lists if they are.
- **Reverts.** A revert's subject is `Revert "<original subject>"` —
  even if the original was bad, the revert quotes it. That is the one
  place quoting is correct.

## 5. Tests

```bash
python3 tests/run_skill_tests.py
```

Fixture tests for every rule, plus the real messages from the
measurement: the 92-character blog-post subject fails R1, its
47-character rewrite passes, the 62-file local-rag import fails R4,
and the 147-file restructure warns on R4 — but still fails R5, because
a generated build stamp rode along with the move.
