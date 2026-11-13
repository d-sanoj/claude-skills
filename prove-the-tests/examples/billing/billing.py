"""Billing helpers for a small shop. Amounts are integer cents.

Spec (the requirement — the only thing the tests may be written from):
- discount_rate: under $100.00 (10,000 cents) -> 0%; $100.00 up to
  but not including $500.00 -> 5%; $500.00 and over -> 10%.
- discounted_price: the amount after the discount, in integer cents.
- is_expired: a card is valid through the LAST day of its expiry
  month. It is expired only on or after the 1st of the next month.

This file has three real bugs. They are the point of the example:
the agent-style tests in test_billing_agent.py are all green anyway.
"""
from datetime import date


def discount_rate(amount_cents):
    if amount_cents <= 10000:  # BUG: $100.00 exactly should get 5%
        return 0
    if amount_cents <= 50000:  # BUG: $500.00 exactly should get 10%
        return 5
    return 10


def discounted_price(amount_cents):
    rate = discount_rate(amount_cents)
    return amount_cents * (100 - rate) // 100


def is_expired(expiry_month, expiry_year, today):
    # BUG: expires the card on the 2nd of its expiry month, not after
    # the last day of that month.
    return date(expiry_year, expiry_month, 1) < today
