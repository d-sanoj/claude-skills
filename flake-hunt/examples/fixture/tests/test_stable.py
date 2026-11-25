"""Stable tests: deterministic, isolated, no clock, no randomness.

These four should pass on every run. If the hunt flags one of them,
the hunt itself is broken -- that is the control group.
"""

from app import add, double


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, 1) == 0


def test_double_zero():
    assert double(0) == 0


def test_double_negative():
    assert double(-4) == -8
