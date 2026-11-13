# Prove-the-tests

Make your coding agent prove its tests can fail before it claims
they pass. Three rules — the expected values come from the
requirement, never the implementation; a new test must fail before
the fix; and the suite must survive a mutation check — plus a small
script that deliberately breaks the code and counts how many breaks
the suite notices.

Built for the blog post ["Your agent's tests agree with its
bugs"](https://sanoj.dev/blog/agent-tests-agree-with-bugs/)
(November 13, 2026): a billing module with three real bugs, a
12-test agent-style suite that goes green on it anyway, and a
10-mutant run that leaves three survivors. The wider evidence: a
June 2026 study of 86,156 agent-authored test patches found weak or
absent oracle signals in 80.2% of them, and Meta's Catching JiTTests
— tests designed to fail — caught 74 serious privacy bugs in the
first half of 2026.

## Install

Copy this folder into `~/.claude/skills/` (every project) or
`<project>/.claude/skills/` (one project):

```bash
cp -r prove-the-tests ~/.claude/skills/
```

Requires Python 3.10+. No packages, no network, no model calls.

## Quick start

```bash
cd ~/.claude/skills/prove-the-tests
python3 scripts/mutant_check.py --target billing.py \
    --tests "python3 -m unittest test_billing_agent" \
    --mutants mutants.json --workdir examples/billing
```

That replays the worked example: baseline green, 7/10 mutants
killed — 70% — with the three survivors all in the one function
the suite only tested with `assertIsNotNone`. On your own code,
point `--target` at the file the diff touched, `--tests` at the
command that runs its tests, and `--mutants` at a JSON list of small
realistic breaks (flip a comparison, swap a return value, nudge a
constant). The script exits 1 when anything survives, so it can
gate a commit or a PR.

The SKILL.md has the full workflow: write spec tests from the
requirement first, watch them fail, fix the code, run the mutation
check, and close the survivors — plus a smell scan for mirror
tests, assertions that assert nothing, and coverage theater.

## What is in here

- `SKILL.md` — the skill: the three rules, the workflow, the smell
  scan, and what a mutation score does not prove.
- `scripts/mutant_check.py` — the mutation checker. Copies the
  target's directory, applies each mutant, runs the tests, reports
  killed/survived and a score. Never touches the originals.
- `examples/billing/` — the worked example: a buggy billing module,
  an agent-style suite that goes green on it, a spec-derived suite
  that fails on exactly the three bugs, the ten mutants, and a
  `FIX.md` with the three-line fix.
- `references/oracle-problem.md` — the oracle problem, the
  eight-category taxonomy, and the study numbers.
- `references/mutation-tools.md` — when to graduate to Stryker,
  mutmut, cosmic-ray, PIT, or cargo-mutants.
- `tests/run_skill_tests.py` — replays the billing example end to
  end and asserts the numbers in SKILL.md §5.

## What was tested

`tests/run_skill_tests.py` passes 9/9: the agent suite is green on
the buggy code with a 7/10 mutation score; the spec suite fails
exactly the three bug tests on the buggy code; after the fix the
spec suite is green with 6/6 applicable mutants killed (four
mutants no longer apply — the fix removed their lines); and the
agent suite fails three tests on the fixed code, because it asserted
the bugs. A live run against a real agent session was **not** tested
here — the skill's rules are written for an agent to follow, and
the first live use is yours to watch.

## Cost

One full test-suite run per mutant, on the files the diff touched.
The billing example's ten mutants take under a second.

## License

MIT. Original work — the skill, the script, and the billing example
are mine. The study, the Meta results, and the issue quoted in the
references are credited there and in the blog post linked above.
