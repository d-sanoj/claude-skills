#!/usr/bin/env python3
"""mutant_check.py — prove a test suite can fail.

Usage:
    python3 mutant_check.py --target billing.py --tests "python3 -m unittest test_billing_agent" --mutants mutants.json [--workdir examples/billing]

For each mutant in the JSON file (a list of {"label", "find", "replace"}),
copy the target's directory to a temp dir, apply the one textual change,
run the test command there, and record whether the suite noticed:

    killed    at least one test failed with the mutation active
    survived  the suite stayed green — a blind spot on that exact line

Exit code 0 means every mutant was killed. Exit code 1 means at least
one survived: the suite has holes, and the report lists them.

Rules the script enforces, because the number is meaningless otherwise:
- The find string must occur exactly once in the target. Zero matches
  means the mutant does not apply; two or more means it is ambiguous.
- The baseline (no mutation) must be green. If the suite is already
  red, every mutant looks "killed" and the check proves nothing — fix
  the suite first, or run it against the fixed code.
- The original files are never touched: everything runs on a copy in
  a temp directory, which is deleted afterwards.

No dependencies beyond Python 3.10+. The test command is yours:
unittest, pytest, vitest, go test — anything that exits non-zero on
failure. Keep it fast: one full suite run per mutant.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def run_tests(command, cwd):
    """Run the test command in cwd. Return (exit_code, tail_of_output)."""
    proc = subprocess.run(command, shell=True, cwd=cwd,
                          capture_output=True, text=True, timeout=300)
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, "\n".join(tail[-3:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True,
                        help="source file to mutate, e.g. billing.py")
    parser.add_argument("--tests", required=True,
                        help="test command, e.g. 'python3 -m unittest test_billing_agent'")
    parser.add_argument("--mutants", required=True,
                        help="JSON file: list of {label, find, replace}")
    parser.add_argument("--workdir", default=".",
                        help="directory holding the target and tests")
    args = parser.parse_args()

    target_path = os.path.join(args.workdir, args.target)
    with open(target_path, encoding="utf-8") as f:
        original = f.read()
    with open(args.mutants, encoding="utf-8") as f:
        mutants = json.load(f)

    tmp = tempfile.mkdtemp(prefix="mutant-check-")
    try:
        shutil.copytree(args.workdir, tmp, dirs_exist_ok=True)
        tmp_target = os.path.join(tmp, args.target)

        code, _ = run_tests(args.tests, tmp)
        if code != 0:
            print("BASELINE RED — the suite already fails before any "
                  "mutation, so the check proves nothing.")
            print("Fix the suite (or run it against fixed code) first.")
            return 2
        print(f"baseline green: {args.tests}")

        killed, survived = [], []
        for mutant in mutants:
            label, find, replace = (mutant["label"], mutant["find"],
                                    mutant["replace"])
            count = original.count(find)
            if count != 1:
                print(f"SKIP  {label}: find string occurs {count}x "
                      f"(must occur exactly once)")
                continue
            with open(tmp_target, "w", encoding="utf-8") as f:
                f.write(original.replace(find, replace))
            code, tail = run_tests(args.tests, tmp)
            if code != 0:
                killed.append(label)
                print(f"KILLED    {label}")
            else:
                survived.append(label)
                print(f"SURVIVED  {label}")
            with open(tmp_target, "w", encoding="utf-8") as f:
                f.write(original)

        total = len(killed) + len(survived)
        score = 100.0 * len(killed) / total if total else 0.0
        print(f"\n{len(killed)}/{total} mutants killed "
              f"— mutation score {score:.0f}%")
        if survived:
            print("Survivors — behaviour your tests never check:")
            for label in survived:
                print(f"  - {label}")
            return 1
        print("Every mutant was caught. The suite can fail.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
