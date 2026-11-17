# Output-eval

Judge a generative model by its outputs, not its loss curve.

A model's loss can fall by half while its outputs stay useless — loss
measures how surprised the model is by the next token, not whether a
finished sample does the job. This skill sets up a fixed three-gate
rubric before sampling, samples with fixed seeds, scores every sample
against the rubric, and tracks the "good%" across runs, so a better
loss number can never again pass for a better model.

Built for the blog post ["I trained a tiny GPT to tell jokes. Three
upgrades later, it still can't."](https://sanoj.dev/blog/tiny-gpt-cant-tell-jokes/)
(November 17, 2026): a tiny GPT trained on short jokes, four runs,
three upgrades — word-level tokens, a 4x bigger vocabulary with 3x
the data, a 2.5x bigger model. Finished samples rose from 4% to 70%. The
share of samples that were actually jokes stayed at **0 of 50**. The
gates moved while the headline didn't — complete 4% → 62% → 68% →
70%, coherent 3 → 9 → 4, joke-shaped 0 → 1 → 0 — and that movement
is what said which lever to pull next. The honest conclusion, after
three upgrades and 0 good jokes, was that next-word prediction at
that scale learns joke surface, not joke structure. The harness made
that conclusion possible; without it, the falling loss curve would
have said the model was working.

Original work, built from the author's own experiment — the rubric,
the verdicts, and the scoring script from
[jokeGPT](https://github.com/d-sanoj/jokeGPT). The worked example in
`examples/jokeGPT/` is the experiment itself: the rubric, all 150
samples across the three word-level runs, their verdicts, and the
recomputed results.

## Install

Copy this folder into `~/.claude/skills/` (every project) or
`<project>/.claude/skills/` (one project):

```bash
cp -r output-eval ~/.claude/skills/
```

Requires Python 3.10+. No packages, no network, no model calls.

## Quick start

1. Copy `scripts/rubric-template.md` to `rubric.md` and fill in the
   third gate (what "does the job" means for your task) and the length
   band — **before** you sample anything.
2. Generate 50 samples with fixed seeds and save them verbatim in
   `samples.json`.
3. Judge every sample in `verdicts.json` — one object per sample with
   `text`, `complete`, `coherent`, `<gate3>`, `good`, and a `note`.
4. Score it:

```bash
python3 scripts/judge_outputs.py --samples samples.json \
    --verdicts verdicts.json --gate3 joke_shaped --out results.json
```

The scorer recomputes the automated signals from the samples,
cross-checks the verdicts (same count, same text, `good` equals the
three gates), and prints the table. Compare runs on good%, and report
all three gates — the gates say *where* a run fails.

## Tests

```bash
python3 tests/run_skill_tests.py
```

Checks the scorer on a small fixture with known verdicts, and
reproduces the three jokeGPT runs from `examples/jokeGPT/` — the
numbers must match the experiment's recorded results exactly
(complete 31/34/35, coherent 3/9/4, joke-shaped 0/1/0, good 0/50
every time).
