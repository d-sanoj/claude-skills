---
name: convention-check
description: Make your coding agent write code that looks like yours. Use when an agent's code keeps drifting from the repo's style, when review comments repeat ("we don't use that logger here"), before merging an agent-authored pull request, or when a repo has no written conventions at all. Extracts the conventions the code already follows, writes them as checkable rules with their counts, and checks the diff against them — a failing exit code, not a paragraph in CLAUDE.md.
---

# Convention-check: rules are checks, not prose

An agent writes good code. It just keeps writing it the way most
projects do, not the way yours does. By the third week the review
comments repeat — "we don't use that logger here", "this should
follow the orders service", "don't call the payments API directly"
— and the agent is not being careless. Your conventions are the
places where you decided to do something different from the default,
and those decisions live in review comments from two years ago, a
wiki page nobody opens, and the head of the engineer who set up the
service. If a convention is not in the files the agent reads, the
agent falls back to the average choice — which is exactly the choice
your team decided against.

The usual fix is to write the rules down in `CLAUDE.md`. That helps,
but it is the weakest channel there is. One write-up of this problem
ranks enforcement mechanisms by how hard they are to ignore:
a formatter that rewrites the file, a linter with a non-zero exit
code, a type system or a structural test, a committed example file —
and last, a rule written in prose in your instructions file, which
the agent ignores frequently. "Prose in a config file is a
suggestion. A failing exit code is a fact." This skill moves every
rule as far up that ladder as it will go: what can be measured from
the code becomes a check the agent runs on its own diff.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/extract_conventions.py" --root . --out .conventions
python3 "$S/check_conventions.py" --rules .conventions/conventions.json \
    --root . --diff
```

Tools: Python 3.10+. No packages, no network, no model calls.
The extractor reads the repo; the checker reads only the changed
files. Both run in under a second on a repo of a hundred files.

## 1. The workflow, in order

**Step 1 — extract, don't assert.** Run the extractor on the repo.
It counts, per dimension: file naming (kebab / PascalCase /
camelCase / snake), declarations (`const` / `let` / `var`),
quote style, semicolons, error handling (`throw` / `return null` /
`console.error` / `process.exit`) per directory, logging per
directory, module system (`import` vs `require()`), and commit
messages (share of non-merge commits with an `Area:` prefix).
A pattern becomes a rule only when it is dominant — at least 80%
of the measured cases, in the scope where it applies. Anything
below that is reported as mixed: a decision for a human, not a
rule for the checker.

**Step 2 — record the outliers.** The extractor lists every place
the repo violates its own dominant pattern. Each one is either a
deliberate exception to record in `CONVENTIONS.md` or the first
thing to fix. Do not delete the outliers from the report to make
the numbers prettier — the outliers are the most useful part. In
the worked example, all eleven `var` uses sit in one file, a
hand-written build script that generates the HTML pages; six
camelCase files sit in model and
service folders next to kebab-case siblings; two PascalCase files
define no class at all. None of that was visible before measuring.

**Step 3 — check the diff, not the repo.** Run the checker on the
files the change touched (`--diff` reads `git diff --name-only`).
It exits 1 with a violation list, or 0 with "clean". Every
violation carries the repo evidence that backs the rule, so the
agent can see *why* it is a rule: "const 1821 of 2187 declarations
(83%)". Run it before claiming the work is done — the same place
you run the tests. A check the agent never runs is tier 5 with
extra steps.

**Step 4 — keep a drift ledger.** When the checker catches
something the rules did not cover, or a review corrects the agent
on the same thing twice, that is a missing rule, not a bad prompt.
Add it in the same PR as the fix: extend the extractor's
measurement if the pattern is countable, or write the rule with
its evidence if it is not. Review changes to `CONVENTIONS.md`
the way you review code, because it shapes every change the agent
makes afterward. And re-extract after a big refactor — conventions
drift, and a stale conventions file is a lie the agent will
obediently follow.

## 2. The rules, and their severity

Every rule carries a severity, because not every measurable
pattern is safely checkable:

| Severity | Meaning | Examples |
| --- | --- | --- |
| hard | Fails the check (exit 1) | `const` over `var`, file naming, no `console.log` in shipped code, no `require()` in an ESM repo, `Area:` commit prefix |
| advisory | Reported, does not fail | Quote style — double quotes cluster in HTML template strings and regexes, and a regex cannot tell those apart from real drift |
| formatter | Not checked here at all | Semicolons, indentation — a formatter owns these; prose about them is noise |

The worked example, measured on a real repo of 94 JavaScript
files and 8,018 lines:

| Rule | Evidence |
| --- | --- |
| `const` over `let`/`var` | `const` 1,821 of 2,187 declarations (83%); `let` 355, `var` 11 |
| Single quotes | 2,425 of 2,654 strings (91%) — advisory |
| Semicolons | 92% of statement lines — formatter |
| File naming | kebab-case 57 files; PascalCase 30, of which 28 define a class of the same name |
| No `console.log` in shipped code | 0 calls in `apps/`, `src/`, `functions/`; 30 calls in `scripts/` and `server/` |
| ESM only | 212 `import` statements, 0 `require()` calls |
| Commit messages | 35 of 37 non-merge commits carry an `Area:` prefix (95%) |

And the mixed patterns, which the extractor refuses to turn into
rules: error handling is split everywhere — `apps/` throws 4
times and returns `null` 15 times, `scripts/` throws 79 times
and returns `null` 15, `src/` returns `null` 9 times and never
throws. No directory clears 80% for any one pattern. If your
`CLAUDE.md` says "handle errors consistently", this is the number
that says you do not have a convention there yet — you have a
decision to make. Write the rule after you decide, not before.

Two more numbers from the same run. The extracted
`CONVENTIONS.md` is 799 tokens; the JavaScript source it describes
is 107,672 — the file is 0.7% of the cost of reading the repo.
And the checker run against the repo's own code reports 19 hard
violations in 9 files, plus 95 advisory notes: the drift was
already there, unnoticed, in a repo its author thought was tidy.
That is the point of the exercise. You do not need a new linter.
You need to know what you already do.

## 3. What it does not prove

- **A clean check does not mean the code is right.** A check can
  say the file is named right and uses `const`; it cannot say the
  change is correct. Conventions are about reviewability, and
  reviewable code is where correctness problems get caught — but
  the check itself catches none of them.
- **The checks are regex heuristics, not a parser.** They skip
  comment-only lines, and a double-quoted string that contains a
  single quote is not a violation. They will still misread exotic
  code — a string that spans lines, a `var` inside a template
  literal. When a check fires on code that is actually fine,
  that is a bug report about the checker: fix the check, do not
  teach the agent to ignore it.
- **A dominant pattern is not necessarily a good one.** If a repo
  is 90% one mediocre pattern, the extractor will bless the
  mediocre pattern. Dominance measures consistency, not quality.
  The 80% threshold keeps the checker from enforcing a coin flip;
  it does not keep it from enforcing a bad habit. Read the
  extracted rules before you commit them.
- **Some conventions cannot be measured this way.** "New endpoints
  copy the structure of `api/orders/`" is a real convention and
  this extractor cannot see it. Those belong in the rules file as
  prose with a named example file — the one place prose earns its
  keep — not as checks.
- **It does not replace a formatter or a linter.** Quote style and
  semicolons are listed so you can see them measured; enforcing
  them belongs to the tool that rewrites the file. If your repo
  has no formatter, adding one is a one-day job that pays for
  itself before any of this matters.

## 4. The sine-portfolio example, end to end

`examples/sine-portfolio/` is the full run against the author's
own repo, with the numbers printed by the actual commands:

| Step | Command | Result |
| --- | --- | --- |
| Extract | `extract_conventions.py --root . --out .conventions` | 9 rules, 799 tokens |
| Check the whole repo | `check_conventions.py --rules conventions.json --root . <94 files>` | 19 hard violations in 9 files, 95 advisory |
| Commit message, bare | `--check-commit-msg "fixed the thing"` | exit 1 — no `Area:` prefix |
| Commit message, prefixed | `--check-commit-msg "Blog: fixed the thing"` | exit 0 |

The 19 hard violations break down as: 11 `var` uses, all in
`scripts/lib/blog.js`, a hand-written build script that generates
the HTML pages, written in an
older style; 6 camelCase service and model files
(`exportData.js`, `glyphFit.js`, `measurePage.js`,
`fitPortrait.js`, `lineArt.js`, `pageLoader.js`); and 2 PascalCase
files that define no class (`Letter.js`, `Timeline.js` — both
export helper functions). `functions/_middleware.js` is exempt:
Cloudflare Pages dictates that name. The full report is in
`examples/sine-portfolio/CHECK-REPORT.md`.

## 5. Testing this skill

`tests/run_skill_tests.py` builds a small fixture repo in a temp
directory — three good files, two `Area:`-prefixed commits —
extracts its conventions, then checks two deliberately bad fixtures
and one advisory-only file against them, and asserts the exact numbers:

- the extractor finds the `const`, single-quote, naming, no-log
  (in `apps/` but not `scripts/`), and commit-message rules;
- the checker is clean on the good files (exit 0);
- `bad-service.js` fails with exactly 2 `JS-DECL` + 1 `JS-NOLOG`
  hard violations and 1 advisory quote note;
- `DateHelpers.js` fails with exactly 1 `JS-NAME` violation;
- `ok-but-quoted.js` passes (exit 0) with 1 advisory note;
- a bare commit message fails, an `Area:`-prefixed one passes.

Run it with `python3 tests/run_skill_tests.py` — it needs no
model, no network, and no packages. 21/21 pass.

What was **not** tested: a live run against a real agent session.
The skill's rules are written for an agent to follow; whether a
given agent runs the checker before claiming done is yours to
watch the first time you use it.
