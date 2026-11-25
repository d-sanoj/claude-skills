#!/usr/bin/env python3
"""flake-hunt: find the flaky test before it eats your morning.

A flaky test is one that both passes and fails on the same code
(Google's definition). A single green run proves nothing about a
test like that -- a test that fails 10% of the time passes a single
run 90% of the time. This script runs the suite N times, counts
per-test outcomes, and names the tests that changed their answer.

Usage:
    python3 flake-hunt.py hunt [PATH] [--runs N] [--out DIR]
        Run the pytest suite at PATH (default: .) N times
        (default: 10) and report every test that both passed and
        failed, plus every test that failed in the suite but passes
        alone (order/shared-state signature). Writes flake-report.md
        and flake-report.json to --out (default: ./flake-hunt-out).
        Exit 0: no flaky test found. Exit 1: at least one found.
        Exit 2: usage error (pytest missing, path has no tests).

    python3 flake-hunt.py isolate NODEID [--runs N] [--dir PATH]
        Run one test alone N times (default: 5) and report its
        pass/fail count. A test that fails alone is time, random, or
        async; a test that passes alone but fails in the suite is
        order or shared state.

    python3 flake-hunt.py quarantine NODEID [--out DIR]
        Print the quarantine entry (pytest marker + ticket text) for
        a confirmed flaky test. It does not edit your files: the
        owner pastes the marker in and files the ticket.

Requires: Python 3.10+, pytest importable by this Python.
No packages, no network, no model calls.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RESULT_RE = re.compile(r"^(\S+::\S+) (PASSED|FAILED|ERROR|SKIPPED)")
HINTS = [
    (re.compile(r"\btime\.sleep\s*\("), "sleep() -- bare sleep waiting on async work"),
    (re.compile(r"\brandom\."), "random.* -- unseeded randomness"),
    (re.compile(r"time\.time\s*\(|datetime\.now\s*\(|date\.today\s*\("),
     "wall clock -- depends on when the test runs"),
    (re.compile(r"threading\.|asyncio\.|concurrent\.futures"),
     "threads/async -- ordering between threads"),
    (re.compile(r"requests\.|urllib|http\.client|socket"),
     "network -- a remote service that may be slow or down"),
    (re.compile(r"open\(|Path\(.*\)\.read|os\.listdir|glob\."),
     "filesystem -- depends on files outside the test"),
]


def run_pytest(pytest_args, cwd):
    """Run pytest -v once; return {nodeid: outcome}."""
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=no",
           "-p", "no:cacheprovider"] + pytest_args
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True,
                              text=True, timeout=600)
    except FileNotFoundError:
        return None
    results = {}
    for line in proc.stdout.splitlines():
        m = RESULT_RE.match(line.strip())
        if m:
            results[m.group(1)] = m.group(2)
    if not results:
        return {"__error__": proc.stdout[-1500:] + proc.stderr[-1500:]}
    return results


def hunt(path, runs):
    """Run the suite N times; return (per_test, first_run)."""
    per_test = {}
    first_run = None
    for i in range(runs):
        res = run_pytest(["."], cwd=path)
        if res is None:
            raise SystemExit("error: pytest is not importable by "
                             f"{sys.executable} -- install pytest first")
        if "__error__" in res:
            raise SystemExit("error: no test results parsed. pytest said:\n"
                             + res["__error__"])
        if i == 0:
            first_run = res
        for nodeid, outcome in res.items():
            slot = per_test.setdefault(nodeid, {"passed": 0, "failed": 0})
            slot["passed" if outcome == "PASSED" else "failed"] += 1
    return per_test, first_run


def isolate(nodeid, runs, path):
    """Run one test alone N times; return (passed, failed).

    A nodeid pytest cannot find is an error, not a failure: counting
    a missing test as failed once produced the verdict "broken, not
    flaky" for a test that simply did not exist under --dir.
    """
    passed = failed = 0
    for _ in range(runs):
        res = run_pytest([nodeid], cwd=path)
        if res is None:
            raise ValueError("pytest is not importable by "
                             f"{sys.executable} -- install pytest first")
        if "__error__" in res:
            if "not found" in res["__error__"]:
                raise ValueError(
                    f"no such test: {nodeid} under {path} -- "
                    "check the nodeid and the --dir it runs in")
            raise ValueError("no test results parsed. pytest said:\n"
                             + res["__error__"])
        if nodeid not in res:
            raise ValueError(
                f"no such test: {nodeid} under {path} -- "
                "check the nodeid and the --dir it runs in")
        outcome = res[nodeid]
        if outcome == "PASSED":
            passed += 1
        else:
            failed += 1
    return passed, failed


def source_hints(path, nodeid):
    """Cheap static hints from the test's source: labelled as hints."""
    try:
        file_part, _, test_name = nodeid.partition("::")
        src = (Path(path) / file_part).read_text()
    except OSError:
        return []
    # Take the test function body, roughly: from "def <name>" to the
    # next top-level def.
    m = re.search(r"(?ms)^def " + re.escape(test_name) + r"\b.*?(?=^def |\Z)",
                  src)
    body = m.group(0) if m else src
    return [label for pat, label in HINTS if pat.search(body)]


def classify(nodeid, in_suite, alone, path):
    """Classify from evidence. Returns (class, evidence).

    The evidence is statistical, so the verdict says what it is:
    a test that passes alone N times can still be a low-rate
    time/random flake that got lucky N times in a row -- the source
    hints are what separates that case from order dependence.
    """
    passed_s, failed_s = in_suite["passed"], in_suite["failed"]
    passed_a, failed_a = alone
    hints = source_hints(path, nodeid)
    if failed_a > 0:
        cls = "fails alone -- time / random / async"
        ev = (f"failed {failed_a}/{passed_a + failed_a} alone, "
              f"{failed_s}/{passed_s + failed_s} in the suite")
    elif hints:
        cls = ("passes alone -- order / shared state is the leading "
               "hypothesis, but the source also suggests a low-rate flake")
        ev = (f"passed {passed_a}/{passed_a + failed_a} alone, "
              f"failed {failed_s}/{passed_s + failed_s} in the suite; "
              f"a flake that fails ~30% of the time still passes "
              f"{passed_a + failed_a} alone-runs "
              f"{round(0.7 ** (passed_a + failed_a) * 100)}% of the time")
    else:
        cls = "order / shared state -- passes alone, fails in suite"
        ev = (f"passed {passed_a}/{passed_a + failed_a} alone, "
              f"failed {failed_s}/{passed_s + failed_s} in the suite")
    if hints:
        ev += "; source hints: " + "; ".join(hints)
    return cls, ev


def quarantine_text(nodeid, cls, ev):
    return (
        f"# Quarantine entry for {nodeid}\n"
        f"# Classification: {cls}\n"
        f"# Evidence: {ev}\n"
        f"# Paste the marker into the test, file a ticket with this\n"
        f"# text, and fix it within a week (Fowler 2011: quarantine\n"
        f"# is a waiting room with an exit, not a place to forget).\n"
        f"@pytest.mark.flaky(reason=\"{cls}\")\n"
        f"# Ticket: [flake] {nodeid} -- {cls}. {ev}\n"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(prog="flake-hunt",
                                 description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("hunt", help="run the suite N times, name the flakes")
    h.add_argument("path", nargs="?", default=".")
    h.add_argument("--runs", type=int, default=10)
    h.add_argument("--out", default="flake-hunt-out")

    iso = sub.add_parser("isolate", help="run one test alone N times")
    iso.add_argument("nodeid")
    iso.add_argument("--runs", type=int, default=5)
    iso.add_argument("--dir", default=".")

    q = sub.add_parser("quarantine", help="print a quarantine entry")
    q.add_argument("nodeid")
    q.add_argument("--classification", default="unclassified")
    q.add_argument("--evidence", default="")

    args = ap.parse_args(argv)

    if args.cmd == "isolate":
        try:
            passed, failed = isolate(args.nodeid, args.runs, args.dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"{args.nodeid}: {passed} passed, {failed} failed "
              f"in {args.runs} runs alone")
        if failed and passed:
            print("FLAKY: fails alone -- time, random, or async.")
        elif failed:
            print("FAILS ALONE every time -- broken, not flaky. Fix it.")
        else:
            print("PASSES ALONE every time -- if it fails in the suite, "
                  "suspect order / shared state.")
        return 0

    if args.cmd == "quarantine":
        print(quarantine_text(args.nodeid, args.classification,
                              args.evidence))
        return 0

    # hunt
    path = Path(args.path)
    if not path.is_dir():
        print(f"error: no such directory: {path}", file=sys.stderr)
        return 2
    if args.runs < 2:
        print("error: --runs must be at least 2", file=sys.stderr)
        return 2
    per_test, first_run = hunt(path, args.runs)

    total = len(per_test)
    # A test is flaky if it both passed and failed; a test that failed
    # every suite run but passes alone is order-dependent, so isolate
    # every test that failed at least once.
    suspects = [n for n, c in per_test.items() if c["failed"] > 0]
    report = {"runs": args.runs, "tests": total,
              "first_run_failed": sorted(n for n, o in first_run.items()
                                         if o != "PASSED"),
              "flaky": []}
    lines = [f"# flake-hunt: {args.runs} runs of {path}",
             f"tests: {total}; first run failed: "
             f"{len(report['first_run_failed'])}",
             ""]
    for nodeid in sorted(suspects):
        alone = isolate(nodeid, 10, path)
        cls, ev = classify(nodeid, per_test[nodeid], alone, path)
        flaky = per_test[nodeid]["failed"] > 0 and per_test[nodeid]["passed"] > 0
        report["flaky"].append({
            "nodeid": nodeid,
            "in_suite": per_test[nodeid],
            "alone_10x": {"passed": alone[0], "failed": alone[1]},
            "flaky_by_definition": flaky,
            "classification": cls,
            "evidence": ev,
        })
        tag = "FLAKY" if flaky else "FAILS-IN-SUITE"
        lines.append(f"## {tag}: {nodeid}")
        lines.append(f"- in suite: {per_test[nodeid]['failed']}/"
                     f"{args.runs} failed")
        lines.append(f"- alone (10x): {alone[1]} failed")
        lines.append(f"- classification: {cls}")
        lines.append(f"- evidence: {ev}")
        lines.append("")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "flake-report.md").write_text("\n".join(lines))
    (out / "flake-report.json").write_text(json.dumps(report, indent=2))
    print("\n".join(lines))
    if report["flaky"]:
        print(f"{len(report['flaky'])} suspect test(s). "
              f"Report in {out}/flake-report.md")
        print("Next: quarantine each one, then fix the test -- "
              "not the code under test, unless the failure is real.")
        return 1
    print(f"No flaky test found in {args.runs} runs "
          f"({total} tests). The suite is boring, which is the goal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
