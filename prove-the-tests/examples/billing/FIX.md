# Fix for examples/billing/billing.py

Apply these three changes. `tests/run_skill_tests.py` applies them
automatically; this file is the human-readable version.

1. `discount_rate`: `if amount_cents <= 10000:` → `if amount_cents < 10000:`
   ($100.00 exactly is in the 5% tier, not the 0% tier.)
2. `discount_rate`: `if amount_cents <= 50000:` → `if amount_cents < 50000:`
   ($500.00 exactly is in the 10% tier, not the 5% tier.)
3. `is_expired`: replace `return date(expiry_year, expiry_month, 1) < today`
   with a first-of-next-month comparison:

```python
if expiry_month == 12:
    first_after = date(expiry_year + 1, 1, 1)
else:
    first_after = date(expiry_year, expiry_month + 1, 1)
return today >= first_after
```

(A card is valid through the last day of its expiry month, so it is
expired only on or after the 1st of the next month.)
