def _discounted_total(items):
    total = 0
    for price in items:
        if price > 100:
            total += price * 0.9
        else:
            total += price
    return total


def invoice_total(items):
    return _discounted_total(items)


def cart_total(items):
    return _discounted_total(items)
