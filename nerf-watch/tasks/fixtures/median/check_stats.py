"""Checks for median(). Run with: python3 check_stats.py"""
from stats import median

assert median([3, 1, 2]) == 2
assert median([4, 1, 3, 2]) == 2.5
assert median([7]) == 7
assert median([1.5, 0.5, 2.5]) == 1.5
print("all median checks passed")
