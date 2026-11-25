"""Deterministic stand-in for a flaky test, for testing flake-hunt.

A real flaky test fails with a probability, which makes it useless
as a test fixture -- a test of the detector must itself be
deterministic. So this one fails on alternate runs: it keeps a
counter in a file next to the test, increments it every run, and
fails when the counter is odd. Across runs it both passes and fails
on unchanged code, which is exactly the property the detector looks
for, but with a schedule a test can rely on.
"""

from pathlib import Path

COUNTER = Path(__file__).with_name("counter.txt")


def test_alternating():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    assert n % 2 == 0, f"run {n + 1} is odd -- simulated flake"


def test_always_passes():
    assert 1 + 1 == 2
