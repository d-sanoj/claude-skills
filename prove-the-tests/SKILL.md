---
name: prove-the-tests
description: Make your coding agent prove its tests can fail before it claims they pass. Use when an agent says "all tests pass", after an agent writes tests, before merging an agent-authored pull request, or whenever a suite is green but you do not trust it. Writes expected values from the requirement (never from the implementation), watches the new test fail first, then runs a mutation check that deliberately breaks the code and counts how many breaks the suite notices.
---

# Prove-the-tests: a green suite is a claim, not evidence

An agent writes your code, then writes the tests for it, then reports
"all tests pass". That sentence is doing a lot of work. The tests were
written by reading the implementation and asserting what it does — so
if the implementation has a bug, the tests faithfully lock the bug in
place and mark it green. A test is only as good as the source of its
expected values, and when the same agent writes both sides, the oracle
*is* the code.

This is not a hypothetical. A June 2026 study of 86,156 test-file
patches from 33,596 agent-authored pull requests found weak or absent
oracle signals in 80.2% of them — the tests run, but they do not
meaningfully check behaviour (Banik, Chowdhury and Shamim, "All
Smoke, No Alarm", arXiv:2606.18168). Meta's answer, in production
since 2026, is to generate tests *designed to fail* — Catching
JiTTests caught 74 serious privacy bugs at the diff stage in the
first half of 2026. And Claude Code issue #7074 is a user reporting
the other half of the problem: the agent modifying tests to make
them pass instead of fixing the implementation.

This skill gives you the small version of that idea, runnable on your
own machine with no packages: three rules, a mutation checker, and a
smell scan. The worked example in `examples/billing/` is the whole
argument in miniature — a billing module with three real bugs, a
12-test agent-style suite that goes green on it, and a 10-mutant run
that leaves three survivors, all in the one function the suite only
tested with `assertIsNotNone`.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/mutant_check.py" --target billing.py \
    --tests "python3 -m unittest test_billing_agent" \
    --mutants mutants.json --workdir examples/billing
```

Tools: Python 3.10+. No packages, no network, no model calls. One
full suite run per mutant, so keep the target small — the files the
diff touched, not the whole repo.

## 1. The three rules

**Rule 1 — the oracle comes from the requirement, never the
implementation.** Before writing a test, write down the expected
value from the spec, the ticket, the docs, or the user's words — in
that order. A test whose expected value was copied from the code's
output is not a test; it is a description of the code. If there is no
requirement to read the value from, the test cannot be written yet:
ask for the requirement first. The spec tests in the billing example
were written this way — `$100.00 gets 5%`, `a card is valid through
the last day of its expiry month` — and they fail on the buggy code.
That failure is the proof they can catch something.

**Rule 2 — red first.** A new test must fail before the fix, and you
must watch it fail. Write the test, run it, see red, then fix the
code and see green. A test you have never seen fail is a test you
have never seen work. If the test passes on the first run, either the
bug is not there or the test is not testing the bug — find out which
before moving on.

**Rule 3 — the suite must prove it can fail.** After the fix, run
the mutation check on the changed files:

```bash
python3 "$S/mutant_check.py" --target <file> \
    --tests "<your test command>" \
    --mutants <mutants.json> --workdir <dir>
```

`mutants.json` is a list of small, realistic breaks — flip `<` to
`<=`, swap a return value, change a constant by one, drop a
condition. The script copies the directory to a temp folder, applies
each break, runs the suite, and reports killed (at least one test
failed) or survived (the suite stayed green). A survivor is a blind
spot on that exact line: write a real assertion for it, or say
plainly that the line is untested. The script exits 1 when anything
survives, so it can gate a commit or a PR. Report the score, not just
the colour: "12 tests green, 7/10 mutants killed" is evidence;
"all tests pass" is a vibe.

## 2. The workflow, in order

1. **Scope it.** The mutation check runs one full suite per mutant.
   Scope it to the files the change touched and the tests that cover
   them. On a big suite, that is the only way it finishes in minutes.
2. **Write the spec tests first.** Expected values from the
   requirement (Rule 1). Run them against the current code and
   confirm they fail where the bug is (Rule 2).
3. **Fix the code.** Now the spec tests go green. If an old test
   fails on the fixed code, read it before touching it: it may be
   asserting the bug. In the billing example, fixing the code breaks
   three agent-written tests — the suite was *defending* the bugs.
   A test that fails on correct code gets rewritten from the
   requirement, never deleted to make the run green.
4. **Write mutants for the diff.** Every changed line gets at least
   one mutant: each comparison flipped, each constant nudged, each
   branch forced. `examples/billing/mutants.json` is the template —
   ten mutants for a 20-line module.
5. **Run the check and close the survivors.** Each survivor gets a
   real assertion or an explicit "untested, accepted" note. Re-run
   until the score is 100% of applicable mutants, or say what is
   left and why.
6. **Report evidence, not adjectives.** The number of tests, the
   mutation score, and the red-first failure are the report. Never
   write "all tests pass" without them.

## 3. The smell scan

Before running mutants, scan the tests for the three patterns that
cover most agent-test failures. They are cheap to find and they point
at the worst tests first:

- **The mirror test.** The expected value is re-derived from the
  implementation — `assert result == function(input)` in disguise,
  or a value copied from the code's output. It can never fail. Fix:
  get the value from the requirement.
- **The assertion that isn't.** `assert result is not None`,
  `assert len(result) > 0`, `assert mock.called`. Technically an
  assertion; catches almost nothing. Fix: assert the value, the
  contents, or the effect.
- **Coverage theater.** The line runs, so coverage counts it, but
  nothing checks the value it produced. High coverage, zero
  confidence. Fix: the mutation check. Coverage says the line ran;
  a killed mutant says the line matters.

Also flag tests that inspect source text (they break when a tool
instruments the file) and tests that were weakened in the same change
— an assertion removed, a case deleted, a mock loosened. A test
edited in the same diff as the code it covers is a suspect until
proven otherwise; see Claude Code issue #7074.

## 4. What it does not prove

- **A high mutation score does not mean the spec is right.** If the
  requirement itself is wrong, you will have a 100% score on the
  wrong behaviour. Mutation testing checks whether the tests detect
  changes; it cannot check whether the intended behaviour is correct.
- **Equivalent mutants exist.** Some changes do not alter behaviour
  (reordering independent statements, `x * 1`). A survivor that is
  genuinely equivalent is fine — note it and move on. Learn to
  recognise them; do not chase 100% by testing trivia.
- **It is slow on big suites.** One run per mutant, and a real tool
  generates hundreds. Scope to the diff, and graduate to a real
  mutation tool (Stryker, mutmut, cosmic-ray, PIT — see
  `references/mutation-tools.md`) when the built-in script's
  hand-written mutants stop being enough. The built-in script is a
  flashlight, not a floodlight.
- **It does not replace reading the tests.** A suite can kill every
  mutant and still test the wrong thing. Read the tests like any
  other code — just start with the survivors, because the machine
  has already ranked them.

## 5. The billing example, end to end

`examples/billing/` is a complete run of the workflow, with the
numbers printed by the actual commands:

| Step | Command | Result |
| --- | --- | --- |
| Agent suite on buggy code | `python3 -m unittest test_billing_agent` | 12 tests, all green |
| Mutation check, agent suite | `mutant_check.py --tests "... test_billing_agent"` | 7/10 killed — 70% |
| Spec suite on buggy code | `python3 -m unittest test_billing_spec` | 12 tests, 3 failures — the three bugs |
| Fix the code, spec suite | `python3 -m unittest test_billing_spec` | 12 tests, all green |
| Mutation check, spec suite | `mutant_check.py --tests "... test_billing_spec"` | 6/6 applicable killed — 100% |
| Agent suite on fixed code | `python3 -m unittest test_billing_agent` | 3 failures — it asserted the bugs |

Four of the ten mutants do not apply to the fixed code — the fix
removed the exact lines they targeted — so the spec suite's score is
6/6 applicable, not 10/10. The script reports skipped mutants
rather than counting them as killed; a mutant that cannot apply
proves nothing.

## 6. Testing this skill

`tests/run_skill_tests.py` replays the billing example end to end
in temp directories and asserts the numbers in §5: the agent suite
is green on the buggy code, its mutation score is 7 killed / 3
survived, the spec suite fails exactly the three bug tests on the
buggy code, and after the fix the spec suite is green with 6/6
applicable mutants killed while the agent suite fails three tests.
Run it with `python3 tests/run_skill_tests.py` — it needs no model,
no network, and no packages.

What was **not** tested: a live run against a real agent session.
The skill's rules are written for an agent to follow; whether a
given agent follows them is yours to check the first time you use
it — watch it write a spec test, watch it go red, and read the
mutation report it produces.
