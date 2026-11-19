#!/usr/bin/env python3
"""Check a commit against the commit-craft rules.

Modes (pick one):
  --ref <sha>            check a commit already in the repo
  --message-file <path>  check a message file (optionally with --diff-stat
                         output of `git diff --cached --numstat`, or file
                         paths after --files)
  --staged               check what is staged, using COMMIT_EDITMSG if it
                         exists, else the message must come from --message-file

Exit 0 when every rule passes, 1 when any rule fails, 2 on usage errors.
Warnings (rename-heavy big commits) do not fail the check. No packages,
no network. The rule functions are importable so a batch driver can
score a whole history with the same logic.

Rules:
  R1  Subject is at most 72 characters.
  R2  Body is at most 5 non-empty lines.
  R3  No co-author trailer, "Generated with" line, or robot emoji.
  R4  At most 10 files, unless the commit is a pure move/rename
      (fewer than 2 insertions per file) — then it is a warning; say
      so in the subject so the warning reads as intended.
  R5  No generated or accidental files: dist/, data/generated/,
      node_modules/, *.pyc, .DS_Store, .specstory/, Aider chat history,
      *.log, credentials or .env files.
"""
import argparse
import subprocess
import sys

MAX_SUBJECT = 72
MAX_BODY_LINES = 5
MAX_FILES = 10

FORBIDDEN_TRAILERS = ("co-authored-by:", "generated with", "🤖")
GENERATED_PREFIXES = ("dist/", "data/generated/", "node_modules/",
                      ".specstory/", ".git/")
GENERATED_SUFFIXES = (".pyc", ".DS_Store", ".aider.chat.history.md",
                      ".log", ".env")
GENERATED_NAMES = ("credentials.json", "credentials.yaml", ".env")


def check_message(subject, body):
    """Return a list of (rule, severity, detail) for a commit message."""
    problems = []
    if not subject.strip():
        problems.append(("R1", "fail", "subject is empty"))
    elif len(subject) > MAX_SUBJECT:
        problems.append(("R1", "fail",
                         f"subject is {len(subject)} chars (max {MAX_SUBJECT})"))
    if subject.strip().endswith("."):
        problems.append(("R1", "fail", "subject ends with a period"))
    body_lines = [ln for ln in body.splitlines() if ln.strip()]
    if len(body_lines) > MAX_BODY_LINES:
        problems.append(("R2", "fail",
                         f"body is {len(body_lines)} lines (max {MAX_BODY_LINES})"))
    lowered = (subject + "\n" + body).lower()
    for trailer in FORBIDDEN_TRAILERS:
        if trailer in lowered:
            problems.append(("R3", "fail",
                             f"message contains {trailer!r}"))
    return problems


def check_files(files, insertions):
    """files: list of paths. insertions: total added lines (int).

    Returns a list of (rule, severity, detail).
    """
    problems = []
    for path in files:
        if (path.startswith(GENERATED_PREFIXES)
                or path.endswith(GENERATED_SUFFIXES)
                or path.split("/")[-1] in GENERATED_NAMES):
            problems.append(("R5", "fail", f"generated/accidental file: {path}"))
    if len(files) > MAX_FILES:
        per_file = insertions / max(len(files), 1)
        if per_file < 2:
            problems.append(("R4", "warn",
                             f"{len(files)} files but only {insertions} "
                             f"insertions ({per_file:.1f} per file) — "
                             "a pure move; say so in the subject"))
        else:
            problems.append(("R4", "fail",
                             f"{len(files)} files, {insertions} insertions "
                             f"— split into one logical change per commit"))
    return problems


def git(*args):
    return subprocess.run(["git", *args], capture_output=True,
                          text=True, check=True).stdout


def load_ref(ref):
    fmt = "%s%x1f%b"
    out = git("log", "-1", f"--pretty=format:{fmt}", ref)
    subject, _, body = out.partition("\x1f")
    stats = git("show", "--format=", "--numstat", ref)
    files, insertions = [], 0
    for line in stats.splitlines():
        if not line.strip():
            continue
        added, _, path = line.split("\t")
        files.append(path)
        if added.isdigit():
            insertions += int(added)
    return subject, body, files, insertions


def load_staged(message_file):
    if message_file:
        text = open(message_file, encoding="utf-8").read()
    else:
        try:
            text = open(".git/COMMIT_EDITMSG", encoding="utf-8").read()
        except FileNotFoundError:
            print("no message: pass --message-file", file=sys.stderr)
            sys.exit(2)
    subject, _, body = text.partition("\n")
    body = body.lstrip("\n")
    stats = git("diff", "--cached", "--numstat")
    files, insertions = [], 0
    for line in stats.splitlines():
        if not line.strip():
            continue
        added, _, path = line.split("\t")
        files.append(path)
        if added.isdigit():
            insertions += int(added)
    return subject, body, files, insertions


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a commit (commit-craft).")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--ref")
    group.add_argument("--message-file")
    group.add_argument("--staged", action="store_true")
    ap.add_argument("--files", nargs="*", default=[],
                    help="files the commit touches (with --message-file)")
    ap.add_argument("--insertions", type=int, default=0,
                    help="inserted lines (with --message-file --files)")
    args = ap.parse_args(argv)

    if args.ref:
        subject, body, files, insertions = load_ref(args.ref)
        label = f"commit {args.ref}"
    elif args.staged:
        subject, body, files, insertions = load_staged(args.message_file)
        label = "staged changes"
    else:
        text = open(args.message_file, encoding="utf-8").read()
        subject, _, body = text.partition("\n")
        body = body.lstrip("\n")
        files, insertions = args.files, args.insertions
        label = args.message_file

    problems = check_message(subject, body) + check_files(files, insertions)
    print(f"{label}: subject {len(subject)} chars, "
          f"{len([l for l in body.splitlines() if l.strip()])} body lines, "
          f"{len(files)} files, {insertions} insertions")
    failed = [p for p in problems if p[1] == "fail"]
    for rule, sev, detail in problems:
        print(f"  {sev.upper()} {rule}: {detail}")
    if failed:
        print(f"FAIL: {len(failed)} rule(s) broken")
        return 1
    if problems:
        print("PASS with warnings")
    else:
        print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
