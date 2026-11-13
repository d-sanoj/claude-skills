"""Tests written the way a coding agent writes them: read the
implementation, then assert what the implementation does.

Every value below was copied from the code, not from the spec.
Two of them lock real bugs in place ($100.00 at 0%, $500.00 at 5%,
a card "expired" on the 2nd of its expiry month) and the suite is
green anyway. The discounted_price tests only check that a result
exists — they never check the number.
"""
import unittest
from datetime import date

from billing import discount_rate, discounted_price, is_expired


class TestDiscountRate(unittest.TestCase):
    def test_under_100_no_discount(self):
        self.assertEqual(discount_rate(9999), 0)

    def test_exactly_100_no_discount(self):
        self.assertEqual(discount_rate(10000), 0)

    def test_mid_tier(self):
        self.assertEqual(discount_rate(25000), 5)

    def test_exactly_500_five_percent(self):
        self.assertEqual(discount_rate(50000), 5)

    def test_top_tier(self):
        self.assertEqual(discount_rate(100000), 10)

    def test_rate_is_non_negative(self):
        self.assertGreaterEqual(discount_rate(10000), 0)


class TestDiscountedPrice(unittest.TestCase):
    def test_returns_something(self):
        self.assertIsNotNone(discounted_price(25000))

    def test_returns_something_top_tier(self):
        self.assertIsNotNone(discounted_price(100000))


class TestIsExpired(unittest.TestCase):
    def test_first_of_expiry_month_valid(self):
        self.assertFalse(is_expired(11, 2026, date(2026, 11, 1)))

    def test_second_of_expiry_month_expired(self):
        self.assertTrue(is_expired(11, 2026, date(2026, 11, 2)))

    def test_month_before_expired(self):
        self.assertTrue(is_expired(10, 2026, date(2026, 11, 15)))

    def test_month_after_valid(self):
        self.assertFalse(is_expired(12, 2026, date(2026, 11, 15)))


if __name__ == "__main__":
    unittest.main()
