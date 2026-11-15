#!/usr/bin/env python3
"""Check changed files against the repo's measured conventions.

Reads the conventions.json written by extract_conventions.py and checks
the files you name — or the files in the current git diff. A rule is
only checked when the extractor found it dominant (>=80%) in this
repo; mixed patterns are never enforced.

Usage:
  python3 check_conventions.py --rules conventions.json <file ...>
  python3 check_conventions.py --rules conventions.json --diff
  python3 check_conventions.py --rules conventions.json --check-commit-msg "Area: summary"

Exit code 0: no violations. Exit code 1: violations listed.
"""

import argparse
import json
import os
import re
import subprocess
import sys

JS_EXTS = (".js", ".mjs", ".ts")


def code_lines(text):
    """(lineno, line) for lines that are not comments. A regex checker
    must not flag the word `var` inside a comment that describes it."""
    for i, ln in enumerate(text.splitlines(), 1):
        stripped = ln.strip()
        if stripped.startswith(("//", "*", "/*")):
            continue
        yield i, ln


def naming_style(basename):
    stem = os.path.splitext(basename)[0]
    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", stem):
        return "kebab"
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", stem):
        return "PascalCase"
    if re.fullmatch(r"[a-z][a-zA-Z0-9]*", stem):
        return "camelCase"
    if re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", stem):
        return "snake"
    return "other"


def check_js_name(path, text, rule):
    """kebab-case, except a file defining one class takes its name.
    Framework-dictated names (_middleware.js) are exempt."""
    base = os.path.basename(path)
    if base.startswith(("_", ".")):
        return []
    style = naming_style(base)
    if style == "kebab":
        return []
    if style == "PascalCase":
        stem = os.path.splitext(base)[0]
        if re.search(r"\bclass\s+" + re.escape(stem) + r"\b", text):
            return []
        return [(f"{path}:1", "JS-NAME",
                 f"PascalCase file '{base}' does not define a class "
                 f"named {stem}; use kebab-case")]
    return [(f"{path}:1", "JS-NAME",
             f"file '{base}' is {style}; this repo uses kebab-case "
             f"(except a file defining one class, which takes the "
             f"class's PascalCase name)")]


def check_js_decl(path, text, rule):
    out = []
    for i, ln in code_lines(text):
        if re.search(r"\bvar\b", ln):
            out.append((f"{path}:{i}", "JS-DECL",
                        f"uses var: {ln.strip()[:80]}"))
    return out


def check_js_quotes(path, text, rule):
    # Flag the non-dominant quote style, unless the string contains
    # the dominant quote character (then the other style is required).
    expected = rule["expected"]
    out = []
    for i, ln in code_lines(text):
        if expected == "single":
            for m in re.finditer(r'"[^"\n]{1,80}"', ln):
                if "'" not in m.group(0):
                    out.append((f"{path}:{i}", "JS-QUOTES",
                                f"double-quoted string with no "
                                f"apostrophe: {m.group(0)[:60]}"))
                    break
        else:
            for m in re.finditer(r"'[^'\n]{1,80}'", ln):
                if '"' not in m.group(0):
                    out.append((f"{path}:{i}", "JS-QUOTES",
                                f"single-quoted string with no double "
                                f"quote inside: {m.group(0)[:60]}"))
                    break
    return out


def check_js_nolog(path, text, rule, root):
    rel = os.path.relpath(path, root) if root else path
    scope = rule["scope"]
    if not (rel == scope or rel.startswith(scope + os.sep)):
        return []
    out = []
    for i, ln in code_lines(text):
        if re.search(r"console\.log\b", ln):
            out.append((f"{path}:{i}", "JS-NOLOG",
                        f"console.log in {scope}/, where the repo "
                        f"never logs it: {ln.strip()[:80]}"))
    return out


def check_js_esm(path, text, rule):
    out = []
    for i, ln in code_lines(text):
        if re.search(r"\brequire\s*\(", ln):
            out.append((f"{path}:{i}", "JS-ESM",
                        f"uses require(): {ln.strip()[:80]}"))
    return out


CHECKS = {"JS-NAME": check_js_name, "JS-DECL": check_js_decl,
          "JS-QUOTES": check_js_quotes, "JS-ESM": check_js_esm}


def check_commit_msg(msg, rule):
    if re.match(r"^[A-Z][A-Za-z /&-]{1,20}?: \S", msg):
        return []
    return [("commit message", "GIT-MSG",
             f"'{msg}' has no Area: prefix; {rule['evidence']}")]


def diff_files():
    out = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                         capture_output=True, text=True, timeout=30)
    return [f for f in out.stdout.splitlines() if f]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--check-commit-msg", default=None)
    ap.add_argument("files", nargs="*")
    args = ap.parse_args()

    with open(args.rules) as fh:
        data = json.load(fh)
    # Rules are a list: several may share an id (JS-NOLOG, one per
    # directory), so keep them grouped, not keyed by id alone.
    rules_by_id = {}
    for r in data["rules"]:
        rules_by_id.setdefault(r["id"], []).append(r)
    evidence = {r["id"]: r["evidence"] for r in data["rules"]}
    root = os.path.abspath(args.root)
    violations = []
    n_checked = 0

    if args.check_commit_msg is not None:
        if "GIT-MSG" in rules_by_id:
            violations += check_commit_msg(args.check_commit_msg,
                                           rules_by_id["GIT-MSG"][0])
        else:
            print("No GIT-MSG rule in this repo's conventions "
                  "(commit prefixes are mixed) — nothing to check.")
            return 0
    else:
        files = list(args.files)
        if args.diff:
            files += diff_files()
        for path in files:
            if not os.path.isfile(path):
                print(f"skip: {path} (not a file)")
                continue
            n_checked += 1
            text = open(path, encoding="utf-8", errors="ignore").read()
            if path.endswith(JS_EXTS):
                for rid, fn in CHECKS.items():
                    if rid in rules_by_id:
                        violations += fn(path, text,
                                         rules_by_id[rid][0])
                for rule in rules_by_id.get("JS-NOLOG", []):
                    violations += check_js_nolog(path, text, rule, root)
            # Python quote rule: flag the non-dominant quote style.
            if path.endswith(".py") and "PY-QUOTES" in rules_by_id:
                expected = rules_by_id["PY-QUOTES"][0]["expected"]
                for i, ln in enumerate(text.splitlines(), 1):
                    if expected == "single":
                        pat, other = r'"[^"\n]{1,80}"', "'"
                    else:
                        pat, other = r"'[^'\n]{1,80}'", '"'
                    for m in re.finditer(pat, ln):
                        if other not in m.group(0):
                            violations.append(
                                (f"{path}:{i}", "PY-QUOTES",
                                 f"{'double' if expected == 'single' else 'single'}-quoted "
                                 f"string with no {other} inside: "
                                 f"{m.group(0)[:60]}"))
                            break

    n_rules = len(data["rules"])
    hard = [v for v in violations
            if rules_by_id[v[1]][0].get("severity", "hard") == "hard"]
    advisory = [v for v in violations
                if rules_by_id[v[1]][0].get("severity", "hard")
                != "hard"]
    for loc, rid, msg in hard:
        print(f"{loc} [{rid}] {msg}")
        print(f"    repo evidence: {evidence[rid]}")
    if advisory:
        print(f"\nAdvisory ({len(advisory)} — reported, does not fail):")
        for loc, rid, msg in advisory:
            print(f"{loc} [{rid}] {msg}")
    if not hard:
        if args.check_commit_msg is not None:
            print("convention-check: commit message OK")
        else:
            print(f"convention-check: clean ({n_rules} rules, "
                  f"{n_checked} file(s) checked"
                  + (f", {len(advisory)} advisory note(s)"
                     if advisory else "") + ")")
        return 0
    print(f"\nconvention-check: {len(hard)} violation(s) in "
          f"{len(set(v[0].split(':')[0] for v in hard))} file(s)"
          + (f" (+{len(advisory)} advisory)" if advisory else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
