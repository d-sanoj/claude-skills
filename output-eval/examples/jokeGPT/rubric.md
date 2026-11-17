# Judging rubric — what counts as a "good" joke (v2)

Written before any v2 sample was seen, so the bar cannot move to
suit the results. Applied identically at every step. Fifty samples
per step, fixed seeds (123 + i), temperature 0.8, top_k 40, top_p 1.0,
unless the step is a decoding sweep (then the setting is recorded
with the samples).

A sample counts as GOOD only if all three hold:

1. **Complete** — ends with `.`, `!`, or `?` and is 20–300
   characters long. Automated (see `quality_signals`); a sample
   that fails this cannot be good.
2. **Coherent** — reads as grammatical English throughout, with no
   garbled or misspelled fragments and no `<unk>` in the text. The
   words must form sensible sentences a reader can follow. A single
   `<unk>` fails this: the model did not produce a real word there.
3. **Joke-shaped** — has a setup and a punchline. It poses a
   question or a scenario and delivers a twist or an answer, or it
   is a one-liner with a clear punchline. It reads as a joke even if
   the joke is weak. A coherent sentence that is not a joke (a plain
   statement, a fragment of an anecdote with no twist) fails this.

`good = complete AND coherent AND joke-shaped`.

## How verdicts are recorded

Every step's 50 samples are saved verbatim in
`experiments/v2-samples/<run_id>.json`. The judge (a human reading
each sample) writes `experiments/v2-samples/<run_id>-verdicts.json`:
one object per sample with `text`, `complete`, `coherent`,
`joke_shaped`, `good`, and a one-line `note` explaining the verdict,
especially for borderline calls. Then
`python scripts/run_v2.py judge <run_id> <verdicts.json>` merges
`good_pct` into `experiments/runs-v2.json`.

## What the numbers mean

- `complete%` is the automated rule-1 rate (cheap, objective).
- `good%` is the judged rate (the target metric). Target: 80%
  (40 of 50). With 50 samples, one sample is 2 points — treat
  differences under ~6 points as noise, and say so.
- `duplicate%` is the share of samples repeating an earlier one.
  A model that memorises one joke and repeats it would score high
  here and low on good% — the two numbers together catch that.
