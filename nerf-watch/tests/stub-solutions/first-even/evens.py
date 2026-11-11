def first_even(numbers):
    for n in numbers:
        if n % 2 == 0:
            return n
    return None
