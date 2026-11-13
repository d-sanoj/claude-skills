# Billing example

A 20-line billing module with three real bugs, two test suites, and
ten mutants. It is the worked example for the skill: run the
commands below and you will see every number SKILL.md §5 claims.

## The module

`billing.py` — `discount_rate`, `discounted_price`, `is_expired`.
The spec is in the module docstring. The bugs:

1. `$100.00` exactly gets 0% instead of 5% (`<= 10000` should be `< 10000`).
2. `$500.00` exactly gets 5% instead of 10% (`<= 50000` should be `< 50000`).
3. A card is treated as expired from the 2nd of its expiry month,
   instead of staying valid through the last day of that month.

## The two suites

- `test_billing_agent.py` — written the way an agent writes tests:
  read the implementation, assert what it does. 12 tests, all green
  on the buggy code. Two of them assert the bugs.
- `test_billing_spec.py` — written from the spec, without reading
  the code. 12 tests; 3 fail on the buggy code (the three bugs
  above), all green after the fix.

## Run it

```bash
cd examples/billing
python3 -m unittest test_billing_agent   # 12 tests, OK — on buggy code
python3 -m unittest test_billing_spec    # 3 failures — the three bugs

python3 ../../scripts/mutant_check.py --target billing.py \
    --tests "python3 -m unittest test_billing_agent" \
    --mutants mutants.json --workdir .
# baseline green, 7/10 mutants killed — 70%.
# The 3 survivors are all in discounted_price, the one function the
# agent suite only tested with assertIsNotNone.
```

Fix the three bugs (see `FIX.md`), then:

```bash
python3 -m unittest test_billing_spec    # 12 tests, OK
python3 ../../scripts/mutant_check.py --target billing.py \
    --tests "python3 -m unittest test_billing_spec" \
    --mutants mutants.json --workdir .
# 6/6 applicable mutants killed — 100%. Four mutants no longer
# apply: the fix removed the exact lines they targeted.

python3 -m unittest test_billing_agent   # 3 failures — the suite
# asserted the bugs, so correct code breaks it.
```

`mutants.json` is the ten breaks: two boundary flips, three return
swaps, one expiry comparison, three `discounted_price` changes, one
expiry-month change.
