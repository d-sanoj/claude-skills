def invoice_total(items):
    total = 0
    for price in items:
        if price > 100:
            total += price * 0.9
        else:
            total += price
    return total


def cart_total(items):
    total = 0
    for price in items:
        if price > 100:
            total += price * 0.9
        else:
            total += price
    return total
