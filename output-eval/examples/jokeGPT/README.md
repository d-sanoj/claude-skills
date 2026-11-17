# Worked example: jokeGPT

The experiment this skill comes from. A tiny GPT trained to tell
jokes ([jokeGPT](https://github.com/d-sanoj/jokeGPT)), evaluated with
exactly the harness in this skill: rubric written before sampling,
50 samples per run at fixed seeds (123 + i), temperature 0.8, top-k
40, every sample judged by a human against the three gates.

## The runs

| run | what changed | params | val loss | complete | coherent | joke-shaped | good |
| --- | --- | --- | --- | --- | --- | --- | --- |
| word-level | word tokens, 10k vocab, 15k jokes | 2,079,488 | 5.026 | 31/50 | 3/50 | 0/50 | **0/50** |
| word-level-50k | 40k vocab, 50k jokes | 5,919,488 | 5.262 | 34/50 | 9/50 | 1/50 | **0/50** |
| word-level-50k-big | d_model 256, 6 layers, 96-word context | 14,997,504 | 5.225 | 35/50 | 4/50 | 0/50 | **0/50** |

(For scale: the character-level v1 that started the sequence scored
val loss 2.064 and 2/50 complete. Its loss is not on the same scale
as these runs — a 95-symbol vocabulary against 10,000 and 40,000
words — which is exactly why the runs are compared on good%, not on
loss.)

## Files

- `rubric.md` — the rubric as written before any v2 sample was seen.
- `word-level.json`, `word-level-50k.json`, `word-level-50k-big.json`
  — the 50 samples per run, verbatim, with their sampling settings.
- `word-level-verdicts.json`, `word-level-50k-verdicts.json`,
  `word-level-50k-big-verdicts.json` — one verdict per sample, with a
  note explaining each call.
- `results.json` — the scorer's output for all three runs.

Reproduce the scoring with:

```bash
python3 ../../scripts/judge_outputs.py --samples word-level-50k.json \
    --verdicts word-level-50k-verdicts.json --gate3 joke_shaped
```

The numbers must come back complete 34, coherent 9, joke-shaped 1,
good 0. `tests/run_skill_tests.py` checks all three runs this way.

## What the gates showed

The headline never moved — 0 good jokes in all three runs — but the
gates did, and they said where each run failed. Word-level tokens
fixed the spelling problem completely (complete 4% → 62%) and the
`<unk>` crutch was the blocker: 44 of 50 samples contained one. A
bigger vocabulary collapsed that to 6 of 50 and tripled coherent
samples (3 → 9), and produced the first joke-shaped sample —
"What do you cross a dog with sex with a light bulb? A baby." — whose
setup is garbled, so it still isn't good. A bigger model bought the
best loss of the 40k-vocabulary runs (5.225) and nothing the rubric can see: coherent fell
9 → 4, joke-shaped 1 → 0. Capacity was not the bottleneck. The
sequence stopped at step 3: the decoding sweep was cancelled and the
full 219k-joke corpus was not run. The conclusion stands on three
upgrades and 0 good jokes — next-word prediction at this scale learns
joke surface, not joke structure.
