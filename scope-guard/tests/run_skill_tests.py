#!/usr/bin/env python3
"""Tests for scope-guard. Run from the skill folder:
  python3 tests/run_skill_tests.py
No packages, no network. Exit 0 when all pass.
Each test builds a throwaway git repo in a temp dir.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "scope-guard.py"

spec = importlib.util.spec_from_file_location("scope_guard", SCRIPT)
sg = importlib.util.module_from_spec(spec)
sys.modules["scope_guard"] = sg
spec.loader.exec_module(sg)

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo)] + list(args),
                   check=True, capture_output=True, text=True)


def make_repo():
    d = Path(tempfile.mkdtemp(prefix="scope-guard-test-"))
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "test@example.com")
    git(d, "config", "user.name", "Test")
    (d / "README.md").write_text("repo\n")
    (d / "src").mkdir()
    (d / "src" / "app.py").write_text("print(1)\n")
    (d / ".github" / "workflows").mkdir(parents=True)
    (d / ".github" / "workflows" / "ci.yml").write_text("ci\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "init")
    return d


SCOPE = """# Scope: fix the off-by-one in src/app.py
## Allowed
- src/app.py
- content/blog/blog-22-11-23-2026/**
## Never touch
- lychee.toml
## Noticed, not changed
- src/other.py looks wrong too, but that is another task
"""


def run_check(repo, ref=None):
    """Run the check in-process and capture stdout. Returns (code, text)."""
    import io
    from contextlib import redirect_stdout
    old = os.getcwd()
    os.chdir(repo)
    try:
        buf = io.StringIO()
        argv = ["check", "--scope", "SCOPE.md"]
        if ref:
            argv += ["--ref", ref]
        with redirect_stdout(buf):
            code = sg.main(argv)
        return code, buf.getvalue()
    finally:
        os.chdir(old)


def run_init(repo):
    old = os.getcwd()
    os.chdir(repo)
    try:
        return sg.main(["init", "--scope", "SCOPE.md"])
    finally:
        os.chdir(old)


# 1. An allowed edit passes.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
check("init ok", run_init(r) == 0)
(r / "src" / "app.py").write_text("print(2)\n")
code, out = run_check(r)
check("allowed edit passes", code == 0, out)
check("allowed edit named", "ALLOWED" in out and "src/app.py" in out, out)

# 2. An unlisted file fails, and the verdict names it.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
run_init(r)
(r / "src" / "app.py").write_text("print(2)\n")
(r / "src" / "other.py").write_text("print(9)\n")
code, out = run_check(r)
check("unlisted edit fails", code == 1, out)
check("unlisted edit named", "UNLISTED" in out and "src/other.py" in out, out)

# 3. A never-touch file fails — including the built-in defaults,
# even when SCOPE.md does not list them.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
run_init(r)
(r / ".github" / "workflows" / "ci.yml").write_text("ci changed\n")
code, out = run_check(r)
check("default never-touch fails", code == 1, out)
check("default never-touch named",
      "NEVER-TOUCH" in out and "ci.yml" in out, out)

# 4. A check-config file listed in SCOPE.md fails even if an allowed
# glob would also match it: never-touch beats allowed.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
run_init(r)
(r / "lychee.toml").write_text("exclude = ['x']\n")
code, out = run_check(r)
check("listed never-touch fails", code == 1, out)
check("never-touch beats allowed",
      "NEVER-TOUCH" in out and "lychee.toml" in out, out)

# 5. A file dirty before init is the user's, not the agent's: ignored.
r = make_repo()
(r / "src" / "notes.txt").write_text("my draft\n")
(r / "SCOPE.md").write_text(SCOPE)
run_init(r)
(r / "src" / "app.py").write_text("print(2)\n")
code, out = run_check(r)
check("baseline file ignored", code == 0, out)
check("baseline not counted", "notes.txt" not in out, out)

# 6. A new file inside an allowed glob passes; outside it fails.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
run_init(r)
post = r / "content" / "blog" / "blog-22-11-23-2026"
post.mkdir(parents=True)
(post / "one-file-in-272.md").write_text("post\n")
code, out = run_check(r)
check("new file in allowed glob passes", code == 0, out)
(post / ".." / "blog-99-01-01-2027").mkdir(parents=True, exist_ok=True)
(r / "content" / "blog" / "blog-99-01-01-2027" / "other.md").write_text("x\n")
code, out = run_check(r)
check("new file outside glob fails", code == 1, out)

# 7. --ref mode: committed work on a branch vs main.
r = make_repo()
(r / "SCOPE.md").write_text(SCOPE)
git(r, "checkout", "-qb", "work")
(r / "src" / "app.py").write_text("print(2)\n")
git(r, "add", "-A")
git(r, "commit", "-qm", "fix")
code, out = run_check(r, ref="main")
check("ref mode allowed passes", code == 0, out)
(r / "src" / "other.py").write_text("print(9)\n")
git(r, "add", "-A")
git(r, "commit", "-qm", "extra")
code, out = run_check(r, ref="main")
check("ref mode unlisted fails", code == 1, out)

# 8. Parsing: task line, both heading styles, parking lot ignored.
task, allowed, never = sg.parse_scope(SCOPE)
check("parse task", task == "fix the off-by-one in src/app.py", task)
check("parse allowed", allowed == ["src/app.py",
      "content/blog/blog-22-11-23-2026/**"], str(allowed))
check("parse never", never == ["lychee.toml"], str(never))
task2, allowed2, never2 = sg.parse_scope(
    "Scope: do the thing\nAllowed:\n- a.py\nNever touch:\n- b.py\n")
check("parse plain sections", (allowed2, never2) == (["a.py"], ["b.py"]),
      str((allowed2, never2)))

# 9. No scope file / no baseline is a usage error, not a pass.
r = make_repo()
code, out = run_check(r)
check("missing scope is error", code == 2, out)
(r / "SCOPE.md").write_text(SCOPE)
code, out = run_check(r)
check("missing baseline is error", code == 2, out)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {', '.join(FAILURES)}")
    sys.exit(1)
print("all tests pass")
