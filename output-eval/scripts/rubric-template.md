# Output-eval rubric template

Copy this file, fill in the blanks, and save it as `rubric.md` **before**
any sample is seen. The bar cannot move to suit the results.

## Task

<!-- What the model is supposed to produce, in one sentence. -->

## Sampling

- Samples per run: 50
- Decoding: temperature ___, top-k ___, top-p ___
- Seeds: fixed (e.g. 123 + i)
- Target: ___% good (___ of 50)
- Stop rule: stop if two consecutive changes each gain under 5 points
  of good%. With 50 samples, one sample is 2 points — treat
  differences under ~6 points as noise.

## The three gates

A sample counts as GOOD only if all three hold.

1. **Complete** — ends with `.`, `!`, or `?` and is ___–___ characters
   long. Automated: the scorer recomputes this from the samples.
2. **Coherent** — reads as grammatical English throughout, with no
   garbled or misspelled fragments and no placeholder tokens (a
   single `<unk>` fails this: the model did not produce a real word
   there).
3. **Task-shaped** (name this gate: `___`) — <!-- what "does the job"
   means for this task: a setup and a punchline, code that runs,
   a summary that covers the point without inventing one. --> A
   coherent sample that is not task-shaped fails this gate.

`good = complete AND coherent AND task-shaped`.

## How verdicts are recorded

Every run's 50 samples are saved verbatim in `samples.json`. The
judge (a human reading each sample) writes `verdicts.json`: one
object per sample with `text`, `complete`, `coherent`, `<gate3>`,
`good`, and a one-line `note` explaining the verdict, especially for
borderline calls. Then:

```bash
python3 scripts/judge_outputs.py --samples samples.json \
    --verdicts verdicts.json --gate3 <gate3> --out results.json
```

## What the numbers mean

- `complete%` is the automated rule-1 rate (cheap, objective).
- `good%` is the judged rate (the target metric).
- `duplicate%` is the share of samples repeating an earlier one. A
  model that memorises one good output and repeats it would score
  high here and low on good% — the two numbers together catch that.
