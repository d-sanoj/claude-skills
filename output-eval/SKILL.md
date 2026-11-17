---
name: output-eval
description: Judge a generative model by its outputs, not its loss curve. Use when a model's loss is falling but you don't know whether its outputs are actually any good, when you are about to tune or scale a model and need a number that survives the change, after any training run before you call it an improvement, or when two models or settings need comparing on what they produce rather than what they predict. Sets up a fixed three-gate rubric before sampling, samples with fixed seeds, scores every sample against the rubric, and tracks the "good%" across runs — so a better loss number can never again pass for a better model.
---

# Output-eval: judge the outputs, not the loss

A model's loss can fall by half while its outputs stay useless. Loss
measures how surprised the model is by the next token, averaged over
the training data. It says nothing about whether a finished sample
does the job — tells the joke, answers the question, compiles, reads
like English. The only honest test is to look at the outputs, one by
one, against a bar you fixed before you saw them.

This skill is the evaluation harness from a real experiment: a tiny
GPT trained to tell jokes ([jokeGPT](https://github.com/d-sanoj/jokeGPT)).
Four runs, three upgrades — word-level tokens, a 4x bigger vocabulary
with 3x the data, a 2.5x bigger model — and the share of finished
samples rose from 4% to 70% while the share of samples that were
actually jokes stayed at **0 of 50**. The harness caught that. The loss curve did not. See
`examples/jokeGPT/` for the full worked example: the rubric, all 150
samples, their verdicts, and the recomputed results.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/judge_outputs.py" --samples samples.json \
    --verdicts verdicts.json --gate3 joke_shaped --out results.json
```

Tools: Python 3.10+. No packages, no network, no model calls.

## 1. Write the rubric before you sample

Decide what "good" means **before** any sample is seen, and write it
down in a rubric file. A sample is good only if it passes all three
gates:

1. **Complete** — finished properly. Ends with terminal punctuation
   (`.`, `!`, `?`) and sits inside a length band (20–300 characters
   for jokes; pick the band that fits your task). This gate is
   automated: the script recomputes it from the samples, so it cannot
   drift from the verdicts.
2. **Coherent** — reads as grammatical English throughout, with no
   garbled or misspelled fragments and no placeholder tokens (a
   single `<unk>` fails this — the model did not produce a real word
   there). Judged by a human reading each sample.
3. **Task-shaped** — does the job it was made for. For jokes that is
   "joke-shaped": a setup and a punchline, reads as a joke even if
   weak. For code it might be "runs and does the thing"; for a
   summary, "covers the point without inventing one". Name this gate
   with `--gate3` and define it in the rubric the same way: a
   coherent sample that is not task-shaped fails this gate.

Copy `scripts/rubric-template.md` and fill in the third gate and the
length band. Lock the target too: the jokeGPT target was 80% good
(40 of 50), with a stop rule — stop if two consecutive changes each
gain under 5 points of good%. With 50 samples, one sample is 2
points, so treat differences under ~6 points as noise and say so.

## 2. Sample with fixed seeds, save verbatim

Generate 50 samples per run at the same decoding settings, with
fixed seeds, and save them verbatim — one JSON list, or an object
with a `"samples"` list — before judging anything. Fixed seeds mean
the same run re-sampled gives the same 50; different runs are
compared on the same footing. Never re-roll a bad batch, and never
edit a sample to make it pass: a sample you fixed by hand is a sample
your model did not produce.

## 3. Judge every sample, with a note

Read each sample and record one verdict object per sample, in the
same order as the samples: `text`, `complete`, `coherent`,
`<gate3>`, `good`, and a one-line `note` explaining the verdict,
especially for borderline calls. `good` is not a fourth opinion —
it is `complete AND coherent AND <gate3>`, and the script checks
that the arithmetic holds. The notes are what make the judgment
auditable: anyone can re-read the sample, the note, and the rubric
and see whether they agree.

## 4. Score, and compare runs on good%

Run the scorer. It recomputes the automated signals from the samples
(complete%, duplicates%, mean length), cross-checks the verdicts
against the samples (same count, same text, verdict complete% matches
recomputed complete%, `good` equals the three gates), and prints the
table:

```
samples: 50   gate3: joke_shaped
  complete:    34  ( 68.0%)
  coherent:     9  ( 18.0%)
  joke_shaped   1  (  2.0%)
  good:         0  (  0.0%)
  duplicates: 0.0%   mean 80.2 chars, 18.1 words
```

Compare runs on **good%**, not on loss — loss is only comparable
between runs with the same vocabulary and the same data, and even
then it measures prediction, not output. Report all three gates, not
just the headline: the gates say *where* a run fails. In the joke
experiment the gates moved while the headline didn't — complete%
4 → 62 → 68 → 70, coherent 3 → 9 → 4, joke-shaped 0 → 1 → 0 — and
that movement is what told the author which lever to pull next.
A run that improves the loss and moves no gate has improved nothing
a user can see.

## 5. What the numbers mean, and what they don't

- **good%** is the judged rate — the target metric, and the only
  number that says the model does the job.
- **complete%** is the automated rule-1 rate (cheap, objective).
  A big jump here with no good% usually means the model learned the
  *shape* of the output, not the substance.
- **duplicate%** is the share of samples repeating an earlier one.
  A model that memorises one good output and repeats it scores high
  here and low on good% — the two numbers together catch that.
- **The gates are where the work is.** If coherent is the bottleneck,
  the fix is vocabulary or decoding; if task-shaped is the
  bottleneck, the fix is data, capacity, or a different approach —
  and if no lever moves the bottleneck after two tries, say so and
  stop. The honest conclusion of the joke experiment, after three
  upgrades and 0 good jokes, was that next-word prediction at that
  scale learns joke surface, not joke structure. The harness made
  that conclusion possible; without it, the falling loss curve would
  have said the model was working.

## 6. Keep the record

One folder per run: `samples.json`, `verdicts.json`, `results.json`,
the rubric, and the decoding settings. The verdicts are the evidence
— keep them, including the bad samples. A score with no samples
behind it is a claim, not a measurement.
