"""Tests written from the SPEC, without reading billing.py.

Every expected value below comes from the requirement in the
module docstring: $100.00 gets 5%, $500.00 gets 10%, a card is
valid through the last day of its expiry month, prices are integer
cents. Written before the fix, these tests FAIL on the buggy code —
that failure is the proof the tests can catch something.
"""
import unittest
from datetime import date

from billing import discount_rate, discounted_price, is_expired


class TestDiscountRate(unittest.TestCase):
    def test_under_100_no_discount(self):
        self.assertEqual(discount_rate(9999), 0)

    def test_exactly_100_gets_five_percent(self):
        self.assertEqual(discount_rate(10000), 5)

    def test_mid_tier(self):
        self.assertEqual(discount_rate(25000), 5)

    def test_exactly_500_gets_ten_percent(self):
        self.assertEqual(discount_rate(50000), 10)

    def test_top_tier(self):
        self.assertEqual(discount_rate(100000), 10)


class TestDiscountedPrice(unittest.TestCase):
    def test_mid_tier_price(self):
        self.assertEqual(discounted_price(25000), 23750)

    def test_top_tier_price(self):
        self.assertEqual(discounted_price(100000), 90000)

    def test_price_is_integer_cents(self):
        self.assertIsInstance(discounted_price(25000), int)


class TestIsExpired(unittest.TestCase):
    def test_last_day_of_expiry_month_valid(self):
        self.assertFalse(is_expired(11, 2026, date(2026, 11, 30)))

    def test_first_of_next_month_expired(self):
        self.assertTrue(is_expired(11, 2026, date(2026, 12, 1)))

    def test_early_in_expiry_year_valid(self):
        self.assertFalse(is_expired(11, 2026, date(2026, 1, 15)))

    def test_month_before_expired(self):
        self.assertTrue(is_expired(10, 2026, date(2026, 11, 15)))


if __name__ == "__main__":
    unittest.main()
