#!/usr/bin/env python3
"""scope-guard: keep a coding agent inside the scope it declared.

An agent that "fixes one function" also touches a config file, bumps a
version, and loosens a test that was in the way — and the tests still
pass, because passing tests was the definition of done. Scope creep is
a different question from correctness: did the agent change only what
it was asked to change?

Usage:
  scope-guard.py init [--scope SCOPE.md] [--baseline .scope-baseline.json]
      Record the files that are already dirty. Those are yours, not the
      agent's, and the check will not blame the agent for them.
      Run this BEFORE the first edit.

  scope-guard.py check [--scope SCOPE.md] [--baseline .scope-baseline.json]
      Compare the working tree against the baseline and the declared
      scope. Exit 0 when every changed file is allowed, exit 1 when
      any file is never-touch or unlisted. Run this BEFORE declaring
      the task done.

  scope-guard.py check --ref main
      Same check, but against a git ref instead of a baseline file:
      for work already committed on a branch.

SCOPE.md format (see examples/scope-example.md):
  # Scope: <one sentence — the task>
  ## Allowed
  - content/blog/blog-22-11-23-2026/**
  ## Never touch
  - lychee.toml
  ## Noticed, not changed
  - (parking lot: drive-by findings go here, not in the diff)

Rules the script enforces:
  * never-touch beats allowed — a file in both lists fails.
  * built-in never-touch defaults (CI workflows, lockfiles, secrets)
    apply even when SCOPE.md does not list them.
  * a file that configures a check your change must pass is
    never-touch unless the task IS the check.

Python 3.10+. No packages, no network, no model calls.
"""
import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path, PurePath

# Files no task may touch unless the task IS about them. These apply
# on top of whatever SCOPE.md lists.
DEFAULT_NEVER_TOUCH = [
    ".github/workflows/**",
    "**/package-lock.json",
    "**/yarn.lock",
    "**/pnpm-lock.yaml",
    "**/poetry.lock",
    "**/Pipfile.lock",
    "**/*.pem",
    "**/*.key",
    "**/id_rsa*",
    "**/*.p12",
]


def run_git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def repo_root(cwd):
    return Path(run_git(["rev-parse", "--show-toplevel"], cwd).strip())


def parse_scope(text):
    """Return (task, allowed, never_touch) from a SCOPE.md document."""
    task, allowed, never = "", [], []
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        low = line.lower()
        if line.startswith("#"):
            head = low.lstrip("#").strip().rstrip(":")
            if head.startswith("scope"):
                task = line.split(":", 1)[1].strip() if ":" in line else ""
                section = None
            elif head == "allowed":
                section = "allowed"
            elif head == "never touch":
                section = "never"
            else:
                section = None
            continue
        if low in ("allowed:", "never touch:"):
            section = "allowed" if low == "allowed:" else "never"
            continue
        if section and (line.startswith("- ") or line.startswith("* ")):
            pat = line[2:].strip()
            if pat:
                (allowed if section == "allowed" else never).append(pat)
    return task, allowed, never


def matches(path, patterns):
    """True if path matches any glob. `**` crosses directories; a bare
    directory pattern (ending in /) matches everything under it."""
    p = PurePath(path)
    for pat in patterns:
        if pat.endswith("/"):
            pat = pat + "**"
        if p.match(pat) or fnmatch.fnmatchcase(path, pat):
            return True
        # A pattern without a slash matches a basename anywhere.
        if "/" not in pat and fnmatch.fnmatchcase(p.name, pat):
            return True
    return False


def status_files(root):
    """(changed, untracked): files dirty in the working tree right now."""
    out = run_git(["status", "--porcelain=v1", "-uall"], root)
    changed, untracked = [], []
    for line in out.splitlines():
        if not line.strip():
            continue
        code, path = line[:2], line[3:].strip().strip('"')
        (untracked if code == "??" else changed).append(path)
    return changed, untracked


def ref_files(root, ref):
    """Files that differ from ref (committed) plus uncommitted changes."""
    out = run_git(["diff", "--name-only", ref], root)
    files = [f for f in out.splitlines() if f.strip()]
    changed, untracked = status_files(root)
    return sorted(set(files) | set(changed) | set(untracked))


def line_counts(root, files, ref=None):
    """path -> (added, deleted) where git can tell us; None for new files."""
    counts = {}
    if ref:
        out = run_git(["diff", "--numstat", ref], root)
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                a, d, path = parts
                counts[path] = (None if a == "-" else int(a),
                                None if d == "-" else int(d))
    else:
        out = run_git(["diff", "--numstat"], root)
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                a, d, path = parts
                counts[path] = (None if a == "-" else int(a),
                                None if d == "-" else int(d))
    for f in files:
        if f not in counts:
            p = root / f
            if p.is_file():
                try:
                    n = sum(1 for _ in open(p, errors="replace"))
                except OSError:
                    n = None
                counts[f] = (n, 0)
            else:
                counts[f] = (None, None)
    return counts


def fmt_count(pair):
    a, d = pair
    if a is None and d is None:
        return ""
    return f"(+{a if a is not None else '?'} -{d if d is not None else '?'})"


def check_scope(root, scope_path, baseline_path, ref):
    if not scope_path.is_file():
        print(f"no scope file: {scope_path} — write one before editing "
              f"(see SCOPE.md in the skill folder)")
        return 2
    task, allowed, never = parse_scope(scope_path.read_text())
    never_all = list(dict.fromkeys(DEFAULT_NEVER_TOUCH + never))
    # The scope file and the baseline file are session scaffolding,
    # never part of the change.
    ignore = {scope_path.name, baseline_path.name} if baseline_path else {scope_path.name}
    if ref:
        changed = [f for f in ref_files(root, ref) if f not in ignore]
        baseline_note = f"against ref {ref}"
    else:
        if not baseline_path.is_file():
            print(f"no baseline: {baseline_path} — run `scope-guard.py init` first")
            return 2
        baseline = set(json.loads(baseline_path.read_text()))
        cur_changed, cur_untracked = status_files(root)
        changed = sorted((set(cur_changed) | set(cur_untracked)) - baseline - ignore)
        baseline_note = f"{len(baseline)} file(s) already dirty at init (yours, ignored)"
    counts = line_counts(root, changed, ref=ref)
    verdicts = []
    for f in changed:
        if matches(f, never_all):
            verdicts.append((f, "NEVER-TOUCH"))
        elif matches(f, allowed):
            verdicts.append((f, "ALLOWED"))
        else:
            verdicts.append((f, "UNLISTED"))
    print(f"SCOPE CHECK: {task or '(no task line in scope file)'}")
    print(f"baseline: {baseline_note}")
    print(f"changed by this session: {len(changed)} file(s)")
    for f, v in verdicts:
        print(f"  {v:<12} {f} {fmt_count(counts.get(f, (None, None)))}")
    bad_never = [f for f, v in verdicts if v == "NEVER-TOUCH"]
    bad_unlisted = [f for f, v in verdicts if v == "UNLISTED"]
    if not bad_never and not bad_unlisted:
        print("PASS: every changed file is in scope.")
        return 0
    print("FAIL: ", end="")
    bits = []
    if bad_never:
        bits.append(f"{len(bad_never)} never-touch: {', '.join(bad_never)}")
    if bad_unlisted:
        bits.append(f"{len(bad_unlisted)} unlisted: {', '.join(bad_unlisted)}")
    print("; ".join(bits))
    print("Revert them, widen the scope with a reason, or ask the owner.")
    return 1


def cmd_init(args):
    root = repo_root(Path.cwd())
    scope = Path(args.scope)
    baseline = Path(args.baseline)
    if not scope.is_file():
        print(f"no scope file: {scope} — write SCOPE.md first")
        return 2
    changed, untracked = status_files(root)
    baseline.write_text(json.dumps(sorted(set(changed) | set(untracked)), indent=2))
    print(f"baseline saved: {len(changed) + len(untracked)} file(s) already dirty "
          f"(yours, ignored by the check)")
    task, allowed, never = parse_scope(scope.read_text())
    print(f"scope: {task or '(no task line)'} — {len(allowed)} allowed pattern(s), "
          f"{len(never)} never-touch pattern(s) (+ {len(DEFAULT_NEVER_TOUCH)} defaults)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scope-guard.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("init", help="record the baseline of already-dirty files")
    pi.add_argument("--scope", default="SCOPE.md")
    pi.add_argument("--baseline", default=".scope-baseline.json")
    pc = sub.add_parser("check", help="check the session's diff against the scope")
    pc.add_argument("--scope", default="SCOPE.md")
    pc.add_argument("--baseline", default=".scope-baseline.json")
    pc.add_argument("--ref", default=None, help="check against a git ref instead of a baseline")
    args = ap.parse_args(argv)
    try:
        root = repo_root(Path.cwd())
    except RuntimeError as e:
        print(f"not a git repo: {e}")
        return 2
    if args.cmd == "init":
        return cmd_init(args)
    scope = Path(args.scope)
    baseline = None if args.ref else Path(args.baseline)
    return check_scope(root, scope, baseline, args.ref)


if __name__ == "__main__":
    sys.exit(main())
