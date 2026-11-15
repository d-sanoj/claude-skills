# Convention-check

Make your coding agent write code that looks like yours. Extract the
conventions your repo already follows — measured, with counts — write
them as checkable rules, and check the diff against them. A failing
exit code, not a paragraph in `CLAUDE.md`.

Built for the blog post ["Your agent's code looks nothing like
yours. Stop writing rules. Write checks."](https://sanoj.dev/blog/your-agents-code-looks-nothing-like-yours/)
(November 15, 2026): a real repo of 94 JavaScript files and 8,018
lines, where the extractor found 9 rules — `const` in 83% of
declarations, single quotes in 91% of strings, kebab-case files with
a PascalCase exception for single-class files, no `console.log` in
shipped code, ESM only, `Area:` commit prefixes in 95% of non-merge
commits — and the checker then found 19 hard violations in 9 files
of that same repo, drift nobody had noticed. Error handling, the
thing most style guides lead with, turned out to be mixed in every
directory and earned no rule at all.

The wider evidence: by the third week of using a coding agent,
review comments start repeating — "we don't use that logger here",
"this should follow the orders service" — because conventions live
in old review comments and people's heads, not in the files the
agent reads. And prose rules are the weakest enforcement there is:
a formatter that rewrites the file, a linter with a non-zero exit
code, and a structural test all beat a paragraph in your
instructions file, which the agent ignores frequently.

## Install

Copy this folder into `~/.claude/skills/` (every project) or
`<project>/.claude/skills/` (one project):

```bash
cp -r convention-check ~/.claude/skills/
```

Requires Python 3.10+. No packages, no network, no model calls.

## Quick start

```bash
cd your-repo
python3 ~/.claude/skills/convention-check/scripts/extract_conventions.py \
    --root . --out .conventions
python3 ~/.claude/skills/convention-check/scripts/check_conventions.py \
    --rules .conventions/conventions.json --root . --diff
```

The first command writes `.conventions/CONVENTIONS.md` (human-readable,
every rule backed by a count) and `.conventions/conventions.json`
(machine-readable rules). The second checks the files in your current
diff and exits 1 with a violation list, or 0 with "clean". Check a
commit message the same way:

```bash
python3 ~/.claude/skills/convention-check/scripts/check_conventions.py \
    --rules .conventions/conventions.json --check-commit-msg "Area: summary"
```

A pattern becomes a rule only when it is dominant — at least 80% of
the measured cases. Anything below that is listed as mixed: a decision
for a human, not a rule for the checker. Rules carry a severity: hard
rules fail the check, advisory rules (quote style) are reported but do
not fail, and formatter rules (semicolons) are listed, not checked.

The SKILL.md has the full workflow: extract, record the outliers as
deliberate exceptions or fix them, check the diff before claiming
done, and keep a drift ledger — when the checker catches something
the rules did not cover, add the rule in the same PR as the fix.

## What is in here

- `SKILL.md` — the skill: the workflow, the severity tiers, the
  worked example's numbers, and what a clean check does not prove.
- `scripts/extract_conventions.py` — the extractor. Walks a repo,
  counts naming, declarations, quotes, semicolons, error handling
  and logging per directory, module system, and commit-message
  shape; writes `CONVENTIONS.md` and `conventions.json`.
- `scripts/check_conventions.py` — the checker. Reads
  `conventions.json`, checks the files you name (or `--diff`), and
  exits 1 on a hard violation. Every violation carries the repo
  evidence behind its rule.
- `examples/sine-portfolio/` — the worked example: the extracted
  `CONVENTIONS.md` and `conventions.json` for the author's own
  repo, and `CHECK-REPORT.md`, the checker's 19-violation report
  on that repo's own code.
- `examples/fixtures/` — two deliberately bad files and one
  advisory-only file, with the violations each one should produce.
- `references/conventions-evidence.md` — the pain-point evidence
  and the related work, credited, and what this skill does
  differently.
- `tests/run_skill_tests.py` — replays the fixture repo end to end
  and asserts the numbers in SKILL.md §4–§5.

## What was tested

`tests/run_skill_tests.py` passes 21/21: the extractor finds the
`const`, single-quote, naming, no-log, and commit-message rules on
a clean fixture repo; the checker is clean on its good files; the
bad fixtures fail with exactly the expected violations (2 `var` +
1 `console.log` in `bad-service.js`, 1 naming violation in
`DateHelpers.js`); the advisory-only file passes; and a bare commit
message fails while an `Area:`-prefixed one passes. A live run
against a real agent session was **not** tested here — whether a
given agent runs the checker before claiming done is yours to
watch the first time you use it.

## Cost

Under a second for a hundred-file repo. The extracted
`CONVENTIONS.md` for the worked example is 799 tokens; the
JavaScript source it describes is 107,672 — 0.7% of the cost of
reading the repo.

## License

MIT. Original work — the skill, the scripts, and the worked
example are mine. The articles quoted in the references are
credited there and in the blog post linked above.
