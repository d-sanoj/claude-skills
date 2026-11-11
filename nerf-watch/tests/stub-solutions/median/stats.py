def median(xs):
    """Return the median of a list of numbers."""
    ordered = sorted(xs)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
