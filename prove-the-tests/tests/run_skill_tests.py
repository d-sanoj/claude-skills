#!/usr/bin/env python3
"""End-to-end test for the prove-the-tests skill.

Replays the billing example in temp directories and asserts the
numbers SKILL.md §5 claims. No model, no network, no packages.
Run: python3 tests/run_skill_tests.py  (from the skill folder)
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(HERE, "examples", "billing")
SCRIPT = os.path.join(HERE, "scripts", "mutant_check.py")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f" — {detail}" if detail else ""))


def run(cmd, cwd):
    proc = subprocess.run(cmd, shell=True, cwd=cwd,
                          capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def apply_fix(path):
    src = open(path, encoding="utf-8").read()
    src = src.replace(
        "if amount_cents <= 10000:  # BUG: $100.00 exactly should get 5%",
        "if amount_cents < 10000:")
    src = src.replace(
        "if amount_cents <= 50000:  # BUG: $500.00 exactly should get 10%",
        "if amount_cents < 50000:")
    old = ("    # BUG: expires the card on the 2nd of its expiry month, not after\n"
           "    # the last day of that month.\n"
           "    return date(expiry_year, expiry_month, 1) < today")
    new = ("    if expiry_month == 12:\n"
           "        first_after = date(expiry_year + 1, 1, 1)\n"
           "    else:\n"
           "        first_after = date(expiry_year, expiry_month + 1, 1)\n"
           "    return today >= first_after")
    assert old in src, "expiry bug text not found — billing.py changed?"
    open(path, "w", encoding="utf-8").write(src.replace(old, new))


def main():
    tmp = tempfile.mkdtemp(prefix="prove-the-tests-")
    try:
        work = os.path.join(tmp, "billing")
        shutil.copytree(EXAMPLE, work)

        # 1. Agent suite green on the buggy code.
        code, out = run("python3 -m unittest test_billing_agent", work)
        check("agent suite green on buggy code", code == 0 and "Ran 12 tests" in out and "\nOK" in out, out.strip().splitlines()[-1] if out.strip() else "")

        # 2. Mutation check on the agent suite: 7 killed, 3 survived.
        code, out = run(
            f"python3 {SCRIPT} --target billing.py "
            "--tests 'python3 -m unittest test_billing_agent' "
            "--mutants mutants.json --workdir .", work)
        check("agent suite mutation score 7/10", code == 1 and "7/10 mutants killed" in out, [l for l in out.splitlines() if "mutants killed" in l][0] if "mutants killed" in out else out[-200:])
        survivors = [l for l in out.splitlines() if l.startswith("SURVIVED")]
        check("agent suite has 3 survivors, all in discounted_price",
              len(survivors) == 3 and all("price" in s for s in survivors),
              f"{len(survivors)} survivors")

        # 3. Spec suite fails exactly the three bug tests on buggy code.
        code, out = run("python3 -m unittest test_billing_spec", work)
        fails = sorted(l.split()[1] for l in out.splitlines() if l.startswith("FAIL:"))
        expected = ["test_exactly_100_gets_five_percent",
                    "test_exactly_500_gets_ten_percent",
                    "test_last_day_of_expiry_month_valid"]
        check("spec suite fails exactly the three bug tests",
              code != 0 and fails == sorted(expected), f"failed: {fails}")

        # 4. Fix the code; spec suite green; mutation check 6/6 applicable.
        apply_fix(os.path.join(work, "billing.py"))
        code, out = run("python3 -m unittest test_billing_spec", work)
        check("spec suite green on fixed code", code == 0 and "\nOK" in out)
        code, out = run(
            f"python3 {SCRIPT} --target billing.py "
            "--tests 'python3 -m unittest test_billing_spec' "
            "--mutants mutants.json --workdir .", work)
        check("spec suite kills 6/6 applicable mutants", code == 0 and "6/6 mutants killed" in out,
              [l for l in out.splitlines() if "mutants killed" in l][0] if "mutants killed" in out else out[-200:])
        check("4 mutants skipped as no longer applicable",
              out.count("SKIP") == 4, f"{out.count('SKIP')} skipped")

        # 5. Agent suite on the fixed code fails the three bug-asserting tests.
        code, out = run("python3 -m unittest test_billing_agent", work)
        fails = sorted(l.split()[1] for l in out.splitlines() if l.startswith("FAIL:"))
        expected = ["test_exactly_100_no_discount",
                    "test_exactly_500_five_percent",
                    "test_second_of_expiry_month_expired"]
        check("agent suite fails 3 tests on fixed code (it asserted the bugs)",
              code != 0 and fails == sorted(expected), f"failed: {fails}")

        # 6. The script never touches the shipped files.
        shipped = open(os.path.join(EXAMPLE, "billing.py"), encoding="utf-8").read()
        check("shipped billing.py still buggy (script works on copies)",
              "<= 10000" in shipped and "BUG" in shipped)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
