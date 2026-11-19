#!/usr/bin/env python3
"""Tests for commit-craft. Run from the skill folder:
  python3 tests/run_skill_tests.py
No packages, no network. Exit 0 when all pass.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "check-commit.py"

spec = importlib.util.spec_from_file_location("check_commit", SCRIPT)
check_commit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_commit)

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def fails(problems, rule):
    return any(p[0] == rule and p[1] == "fail" for p in problems)


def warns(problems, rule):
    return any(p[0] == rule and p[1] == "warn" for p in problems)


# ---- R1: subject length and trailing period ----
check("R1 clean subject passes",
      not check_commit.check_message("Fix the loader race", ""))
check("R1 72-char subject passes",
      not check_commit.check_message("x" * 72, ""))
check("R1 73-char subject fails",
      fails(check_commit.check_message("x" * 73, ""), "R1"))
check("R1 trailing period fails",
      fails(check_commit.check_message("Fix the loader race.", ""), "R1"))
check("R1 empty subject fails",
      fails(check_commit.check_message("", ""), "R1"))

# ---- R2: body length ----
check("R2 5-line body passes",
      not check_commit.check_message("Fix it", "a\nb\nc\nd\ne"))
check("R2 6-line body fails",
      fails(check_commit.check_message("Fix it", "a\nb\nc\nd\ne\nf"), "R2"))
check("R2 blank lines do not count",
      not check_commit.check_message("Fix it", "a\n\n\nb\n\n"))

# ---- R3: trailers and tool credit ----
check("R3 co-author trailer fails",
      fails(check_commit.check_message(
          "Fix it", "Why.\n\nCo-Authored-By: Claude <x@y.z>"), "R3"))
check("R3 generated-with line fails",
      fails(check_commit.check_message(
          "Fix it", "Generated with Claude Code"), "R3"))
check("R3 robot emoji fails",
      fails(check_commit.check_message("Fix it 🤖", ""), "R3"))

# ---- R4: file count, with the rename exception ----
check("R4 10 files pass",
      not check_commit.check_files([f"f{i}.py" for i in range(10)], 100))
check("R4 11 files fail",
      fails(check_commit.check_files([f"f{i}.py" for i in range(11)], 100), "R4"))
check("R4 rename-heavy big commit warns, not fails",
      warns(check_commit.check_files([f"f{i}.py" for i in range(147)], 204), "R4")
      and not fails(check_commit.check_files(
          [f"f{i}.py" for i in range(147)], 204), "R4"))

# ---- R5: generated and accidental files ----
for bad in ["dist/bundle.js", "data/generated/x.json", "node_modules/a/b.js",
            "x.pyc", ".DS_Store", ".specstory/history/1.md",
            ".aider.chat.history.md", "server.log", "credentials.json"]:
    check(f"R5 flags {bad}",
          fails(check_commit.check_files([bad], 1), "R5"))
check("R5 clean files pass",
      not check_commit.check_files(["app/api.py", "README.md"], 40))

# ---- Real messages from the measurement (Nov 5–18, 2026) ----
LONG_SUBJECT = ("Add blog post: Your agent's code looks nothing like "
                "yours. Stop writing rules. Write checks.")
REWRITE = "Blog: your agent's code needs checks, not rules"
check("real 92-char blog subject fails R1",
      len(LONG_SUBJECT) == 92
      and fails(check_commit.check_message(LONG_SUBJECT, ""), "R1"))
check("real 47-char rewrite passes",
      len(REWRITE) == 47
      and not check_commit.check_message(REWRITE, ""))
LONG_BODY = "\n".join(f"line {i}" for i in range(13))
check("real 13-line CI body fails R2",
      fails(check_commit.check_message(
          "Add CI pipeline, example data, and Streamlit GUI", LONG_BODY), "R2"))
check("real 62-file import fails R4",
      fails(check_commit.check_files([f"f{i}" for i in range(62)], 3941), "R4"))
check("real 147-file restructure warns on R4, not fails",
      warns(check_commit.check_files([f"f{i}" for i in range(147)], 204), "R4")
      and not fails(check_commit.check_files(
          [f"f{i}" for i in range(147)], 204), "R4"))
check("real restructure still fails R5 on its stowaway stamp file",
      fails(check_commit.check_files(
          ["content/blog/blog-1-11-03-2026/x.md",
           "data/generated/home-stamp.txt"], 204), "R5"))

print()
if FAILURES:
    print(f"{len(FAILURES)} test(s) failed: {FAILURES}")
    sys.exit(1)
print("all tests pass")
