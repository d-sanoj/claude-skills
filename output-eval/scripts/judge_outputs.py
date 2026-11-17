#!/usr/bin/env python3
"""judge_outputs.py — score a batch of generated samples against a fixed
rubric, and check the verdicts against the samples.

The rubric has three gates, and a sample is GOOD only if it passes all
three:

  1. complete    — finished properly (ends with terminal punctuation,
                   within a length band). Recomputed from the samples,
                   so it cannot drift from the verdicts.
  2. coherent    — reads as grammatical English throughout, no garbled
                   fragments, no placeholder tokens (e.g. <unk>).
                   Judged by a human, one verdict per sample.
  3. <gate3>     — the task-shaped gate, named with --gate3 (default
                   "task_shaped"): the sample does the job it was made
                   for. For jokes that is "joke_shaped" (setup +
                   punchline); for code it might be "runs"; for a
                   summary, "covers the point". Judged by a human.

Usage:
  python3 judge_outputs.py --samples samples.json --verdicts verdicts.json \\
      [--gate3 joke_shaped] [--min-chars 20] [--max-chars 300] \\
      [--out results.json]

Inputs:
  samples.json   a JSON list of strings, or an object with a "samples"
                 list (the jokeGPT sample files use the latter).
  verdicts.json  a JSON list of one object per sample, in the same
                 order, each with "text", "complete", "coherent",
                 "<gate3>", "good", and a "note" explaining the
                 verdict, especially for borderline calls.

Output: prints a table and, with --out, writes results.json with the
counts and percentages. Exit code 0 when the verdicts agree with the
samples (same count, same text, recomputed complete% matches the
verdicts); 1 otherwise. A sample whose "good" is true must pass all
three gates, and vice versa — the script checks that too.

The point of the ceremony: the rubric is written BEFORE any sample is
seen, the samples are saved verbatim, and the numbers are recomputed
from the files — so the headline (good%) cannot quietly move to suit
the results, and anyone can re-run the scoring and get the same
answer. See examples/jokeGPT/ for a worked example: three runs of a
tiny joke-telling GPT, 50 samples each, good% 0 every time.
"""
import argparse
import json
import re
import sys

TERMINAL = (".", "!", "?")


def load_samples(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data["samples"]
    return data


def normalise(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def quality_signals(samples, min_chars, max_chars):
    """Automated signals, recomputed from the samples every time."""
    n = len(samples)
    if n == 0:
        return {"n_samples": 0, "complete_pct": 0.0, "duplicate_pct": 0.0,
                "mean_chars": 0.0, "mean_words": 0.0}
    complete = sum(1 for s in samples
                   if min_chars <= len(s) <= max_chars
                   and s.endswith(TERMINAL))
    seen, duplicates = set(), 0
    for s in samples:
        norm = normalise(s)
        if norm in seen:
            duplicates += 1
        seen.add(norm)
    return {
        "n_samples": n,
        "complete_pct": round(100 * complete / n, 1),
        "duplicate_pct": round(100 * duplicates / n, 1),
        "mean_chars": round(sum(len(s) for s in samples) / n, 1),
        "mean_words": round(sum(len(s.split()) for s in samples) / n, 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--gate3", default="task_shaped",
                    help="name of the third gate (default: task_shaped)")
    ap.add_argument("--min-chars", type=int, default=20)
    ap.add_argument("--max-chars", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    samples = load_samples(args.samples)
    with open(args.verdicts, encoding="utf-8") as f:
        verdicts = json.load(f)

    errors = []
    if len(verdicts) != len(samples):
        errors.append(f"verdicts ({len(verdicts)}) != samples ({len(samples)})")
    for i, (s, v) in enumerate(zip(samples, verdicts)):
        if v.get("text") != s:
            errors.append(f"sample {i}: verdict text does not match sample")
            break
        for key in ("complete", "coherent", args.gate3, "good"):
            if key not in v:
                errors.append(f"sample {i}: verdict missing key {key!r}")
        if errors:
            break
        expect_good = bool(v["complete"] and v["coherent"] and v[args.gate3])
        if bool(v["good"]) != expect_good:
            errors.append(
                f"sample {i}: good={v['good']} but gates say {expect_good} "
                f"(complete={v['complete']}, coherent={v['coherent']}, "
                f"{args.gate3}={v[args.gate3]})")
            break

    signals = quality_signals(samples, args.min_chars, args.max_chars)
    n = len(samples)
    counts = {
        "n": n,
        "complete": sum(1 for v in verdicts if v.get("complete")),
        "coherent": sum(1 for v in verdicts if v.get("coherent")),
        args.gate3: sum(1 for v in verdicts if v.get(args.gate3)),
        "good": sum(1 for v in verdicts if v.get("good")),
    }
    if n and counts["complete"] != round(signals["complete_pct"] / 100 * n):
        errors.append(
            f"verdict complete count ({counts['complete']}) disagrees with "
            f"recomputed complete% ({signals['complete_pct']}) — "
            f"recheck the length band or the verdicts")

    pct = {k: round(100 * v / n, 1) if n else 0.0 for k, v in counts.items()
           if k != "n"}
    results = {"gate3": args.gate3, "counts": counts, "pct": pct,
               "signals": signals}
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    print(f"samples: {n}   gate3: {args.gate3}")
    print(f"  complete:   {counts['complete']:>3}  ({pct['complete']:>5}%)")
    print(f"  coherent:   {counts['coherent']:>3}  ({pct['coherent']:>5}%)")
    print(f"  {args.gate3:<12} {counts[args.gate3]:>3}  ({pct[args.gate3]:>5}%)")
    print(f"  good:       {counts['good']:>3}  ({pct['good']:>5}%)")
    print(f"  duplicates: {signals['duplicate_pct']}%   "
          f"mean {signals['mean_chars']} chars, {signals['mean_words']} words")
    if errors:
        print("MISMATCH:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("verdicts agree with the samples.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
