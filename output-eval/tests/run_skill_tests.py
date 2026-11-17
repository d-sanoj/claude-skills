#!/usr/bin/env python3
"""Tests for output-eval. Run from the skill folder:
  python3 tests/run_skill_tests.py
No packages, no network. Exit 0 when all pass.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "judge_outputs.py"
EXAMPLES = SKILL / "examples" / "jokeGPT"

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def run_script(samples, verdicts, gate3="task_shaped", extra=None):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "results.json"
        cmd = [sys.executable, str(SCRIPT), "--samples", str(samples),
               "--verdicts", str(verdicts), "--gate3", gate3,
               "--out", str(out)] + (extra or [])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        results = json.loads(out.read_text()) if out.exists() else None
        return proc.returncode, proc.stdout, results


def fixture_test():
    """Small fixture with known verdicts: 5 samples, 4 complete,
    4 coherent, 1 task-shaped, 1 good, 1 duplicate."""
    samples = [
        "The quick brown fox jumps over the lazy dog.",
        "The quick brown fox jumps over the lazy dog.",
        "A half-finished thought with no ending",
        "Glkjh qzxwplm vbnr tgyhuj ikolp.",
        "Why did the chicken cross the road? To get to the other side!",
    ]
    verdicts = [
        {"text": samples[0], "complete": True, "coherent": True,
         "task_shaped": False, "good": False,
         "note": "Finished and grammatical, but not task-shaped."},
        {"text": samples[1], "complete": True, "coherent": True,
         "task_shaped": False, "good": False,
         "note": "Duplicate of sample 0, still not task-shaped."},
        {"text": samples[2], "complete": False, "coherent": True,
         "task_shaped": False, "good": False,
         "note": "No terminal punctuation, so not complete."},
        {"text": samples[3], "complete": True, "coherent": False,
         "task_shaped": False, "good": False,
         "note": "Ends with a period but the words are nonsense."},
        {"text": samples[4], "complete": True, "coherent": True,
         "task_shaped": True, "good": True,
         "note": "Setup and punchline, a real joke."},
    ]
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "samples.json"
        v = Path(td) / "verdicts.json"
        s.write_text(json.dumps(samples))
        v.write_text(json.dumps(verdicts))
        rc, stdout, results = run_script(s, v)
    check("fixture exit 0", rc == 0, stdout)
    check("fixture counts", results and results["counts"] == {
        "n": 5, "complete": 4, "coherent": 4, "task_shaped": 1, "good": 1},
        str(results))
    check("fixture duplicate%", results and results["signals"]["duplicate_pct"] == 20.0,
          str(results))


def mismatch_test():
    """A verdict claiming good without all three gates must fail."""
    samples = ["A perfectly fine sentence that does the job."]
    verdicts = [{"text": samples[0], "complete": True, "coherent": True,
                 "task_shaped": False, "good": True,
                 "note": "Claims good while failing the third gate."}]
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "samples.json"
        v = Path(td) / "verdicts.json"
        s.write_text(json.dumps(samples))
        v.write_text(json.dumps(verdicts))
        rc, stdout, _ = run_script(s, v)
    check("good-without-gates fails", rc == 1, stdout)
    check("mismatch reported", "MISMATCH" in stdout, stdout)


def jokegpt_regression():
    """Reproduce the three jokeGPT runs from the worked example.
    The numbers must match the experiment's recorded results exactly."""
    expected = {
        "word-level": {"complete": 31, "coherent": 3, "joke_shaped": 0, "good": 0},
        "word-level-50k": {"complete": 34, "coherent": 9, "joke_shaped": 1, "good": 0},
        "word-level-50k-big": {"complete": 35, "coherent": 4, "joke_shaped": 0, "good": 0},
    }
    for run_id, want in expected.items():
        rc, stdout, results = run_script(
            EXAMPLES / f"{run_id}.json",
            EXAMPLES / f"{run_id}-verdicts.json", gate3="joke_shaped")
        got = {k: results["counts"][k] for k in want} if results else None
        check(f"jokeGPT {run_id} exit 0", rc == 0, stdout)
        check(f"jokeGPT {run_id} counts {want}", got == want, str(got))


if __name__ == "__main__":
    fixture_test()
    mismatch_test()
    jokegpt_regression()
    print(f"\n{len(FAILURES)} failure(s)" if FAILURES else "\nall tests passed")
    sys.exit(1 if FAILURES else 0)
