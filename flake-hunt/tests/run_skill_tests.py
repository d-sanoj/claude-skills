#!/usr/bin/env python3
"""Tests for the flake-hunt skill (run: python3 tests/run_skill_tests.py).

Covers the detector end to end on a deterministic fixture (a test
that fails on alternate runs), the parser and classifier on synthetic
input, and the quarantine text. No network, no model calls. Needs
pytest importable by this Python.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import importlib.util

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "flake-hunt.py"
FIXTURE = HERE / "fixtures" / "alternating"

_spec = importlib.util.spec_from_file_location("flake_hunt", SCRIPT)
flake_hunt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flake_hunt)


def run(cmd, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=300)
    return proc


def test_hunt_flags_alternating_test():
    with tempfile.TemporaryDirectory() as tmp:
        # Copy the deterministic fixture (counter starts absent).
        import shutil
        shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True)
        proc = run([sys.executable, str(SCRIPT), "hunt", tmp,
                    "--runs", "6", "--out", str(Path(tmp) / "out")])
        assert proc.returncode == 1, proc.stdout + proc.stderr
        report = json.loads((Path(tmp) / "out" / "flake-report.json")
                            .read_text())
        flagged = {f["nodeid"] for f in report["flaky"]}
        assert any("test_alternating" in n for n in flagged), flagged
        assert not any("test_always_passes" in n for n in flagged), flagged
        entry = next(f for f in report["flaky"]
                     if "test_alternating" in f["nodeid"])
        assert entry["flaky_by_definition"] is True
        assert entry["in_suite"] == {"passed": 3, "failed": 3}, entry


def test_hunt_clean_suite_passes():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "test_clean.py").write_text(
            "def test_one():\n    assert True\n"
            "def test_two():\n    assert 1 + 1 == 2\n")
        proc = run([sys.executable, str(SCRIPT), "hunt", tmp,
                    "--runs", "3", "--out", str(Path(tmp) / "out")])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "No flaky test found" in proc.stdout


def test_isolate_command():
    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True)
        proc = run([sys.executable, str(SCRIPT), "isolate",
                    "test_alternating.py::test_alternating",
                    "--runs", "4", "--dir", tmp])
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "2 passed, 2 failed" in proc.stdout, proc.stdout


def test_classify_fails_alone_vs_order():
    alone = flake_hunt.classify(
        "test_x.py::test_time", {"passed": 7, "failed": 3},
        (3, 2), ".")
    assert alone[0].startswith("fails alone"), alone
    order = flake_hunt.classify(
        "test_x.py::test_order", {"passed": 0, "failed": 10},
        (5, 0), ".")
    assert order[0].startswith("order / shared state"), order


def test_quarantine_text_names_the_test():
    text = flake_hunt.quarantine_text(
        "test_x.py::test_time", "fails alone", "failed 2/5 alone")
    assert "test_x.py::test_time" in text
    assert "pytest.mark.flaky" in text


def test_isolate_missing_test_errors():
    # Regression test: a nodeid pytest cannot find used to count as
    # "failed", producing the false verdict "broken, not flaky".
    with tempfile.TemporaryDirectory() as tmp:
        import shutil
        shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True)
        proc = run([sys.executable, str(SCRIPT), "isolate",
                    "test_alternating.py::test_nope",
                    "--runs", "2", "--dir", tmp])
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "no such test" in proc.stderr, proc.stderr
        assert "broken, not flaky" not in proc.stdout


def test_hunt_rejects_bad_path():
    proc = run([sys.executable, str(SCRIPT), "hunt", "/no/such/dir",
                "--runs", "3"])
    assert proc.returncode == 2, proc.stdout + proc.stderr


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
