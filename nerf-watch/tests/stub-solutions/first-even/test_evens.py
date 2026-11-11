"""Checks for first_even(). Run with: python3 test_evens.py"""
from evens import first_even

assert first_even([]) is None
assert first_even([1, 3, 5]) is None
assert first_even([1, 4, 6]) == 4
print("all first_even checks passed")
