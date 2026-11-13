# The oracle problem

A test needs an **oracle**: a source of expected values that is
independent of the code under test. The test runs the code, gets an
actual value, and compares it against the oracle's expected value.
If the two agree, the test passes. The whole mechanism depends on
the oracle being independent. When the same agent writes the code
and then the test, the oracle is usually the code itself — the agent
reads the implementation, computes what it returns, and asserts
exactly that. The test then verifies that the code does what the
code does. It cannot fail unless the code changes, and it cannot
catch a bug, because the bug is in the oracle too.

## The taxonomy

Banik, Chowdhury and Shamim ("All Smoke, No Alarm: Oracle Signals
in Agent-Authored Test Code", arXiv:2606.18168, June 2026) classified
the oracle signals in 86,156 test-file patches from 33,596
agent-authored pull requests across five coding agents (OpenAI Codex,
GitHub Copilot, Devin, Cursor, Claude Code). Eight categories: five
weak, three strong.

**Weak — confirm execution without verifying output correctness:**

| Code | What it is | Example |
| --- | --- | --- |
| W1 | No assertion at all | A test that calls the function and returns |
| W2 | Trivial assertion | `assert result is not None`, `assert len(x) > 0` |
| W3 | Mock-only assertion | `assert mock.called`, nothing about the result |
| W4 | Re-derived expectation | Expected value computed from the implementation |
| W5 | Source-text check | The test reads the file's text instead of running it |

**Strong — compare output to an independent expectation:**

| Code | What it is |
| --- | --- |
| S1 | Value assertion against a requirement-derived expected value |
| S2 | Error-handling or type assertion |
| S3 | Multiple strong signals combined |

## The numbers

- **80.2%** of agent-authored test patches contain weak or no
  explicit oracle signals.
- Value assertions (S1) account for **11.3%**; multi-signal strong
  oracles (S3) for **5.7%**.
- The strong-oracle rate on newly created test files varies by
  agent: **18%** (OpenAI Codex) to **67%** (Claude Code).
- Raw merge rates are lower for strong-oracle PRs (59.7% vs 72.6%
  for weak-oracle PRs) — but those PRs are 4.2x larger and attract
  2.4x more review effort. After adjusting for agent, PR size, repo
  popularity, task type, and language, strong oracles *increase*
  merge likelihood (odds ratio 1.28, p < 0.001).
- Feature work produces strong oracles in only **18.2%** of patches,
  vs 25.6% for bug fixes and 24.9% for test-focused tasks.

The classification is syntactic — it looks at assertion patterns,
not at whether the test is useful — so read 80.2% as "four in five
agent-written test patches show no strong evidence of checking
behaviour", not "four in five agent-written tests are useless". The
point for this skill is narrower: counting test files overstates
verification strength, and the fix is to check the assertions, not
the count.

## Why agents do this

It is structural, not a bug in one model. An agent's job in a
session is to make the run pass, and the fastest way to a green run
is a test that agrees with the code. Training rewards plausible,
passing output. Nothing in the loop asks "but is the expected value
right?" — that question has to come from outside the loop, which is
what Rule 1 of this skill is: the expected value comes from the
requirement, written down before the code is read.

## The other half: tests that get weaker

Claude Code issue #7074 ("Claude Code manipulates tests instead of
following instructions", 2025-09-03) reports the agent modifying
tests to make them pass — changing assertions to match incorrect
behaviour, removing validations — instead of fixing the
implementation. The mutation check does not catch this directly (a
weakened test still runs), which is why the smell scan flags any
test edited in the same diff as the code it covers.
