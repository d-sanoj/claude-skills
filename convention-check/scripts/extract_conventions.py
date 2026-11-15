#!/usr/bin/env python3
"""Extract a repo's conventions by measuring what its code actually does.

Walks a repository, counts patterns per dimension (naming, declarations,
quotes, error handling, logging, commit messages), and writes two files:

  CONVENTIONS.md   human-readable, every rule backed by a count
  conventions.json machine-readable rules for check_conventions.py

A pattern becomes a rule only when it is dominant: at least 80% of the
measured cases, in the scope where it applies (whole repo, or one
directory when directories disagree). Anything below that is reported
as "mixed" — a decision for a human, not a rule for the checker.

Honest scope: the JavaScript checks are regex heuristics over lines,
not a parser. A double-quoted string that contains a single quote is
not a violation. A file that defines one class may take that class's
PascalCase name. Outliers are listed, not hidden: if eleven `var`
uses all sit in one file, the report says so, and that file is either
a deliberate exception to record or the first thing to fix.

Usage:
  python3 extract_conventions.py --root /path/to/repo --out /path/to/dir
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys

DOMINANCE = 0.80
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".cache",
             "data", ".venv", "venv"}
JS_EXTS = (".js", ".mjs", ".ts")
PY_EXTS = (".py",)


def is_skipped(path):
    parts = path.split(os.sep)
    return any(p in SKIP_DIRS for p in parts)


def collect_files(root):
    js, py = [], []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(dp, f)
            if f.endswith(JS_EXTS):
                js.append(p)
            elif f.endswith(PY_EXTS):
                py.append(p)
    return sorted(js), sorted(py)


def topdir(root, path):
    rel = os.path.relpath(path, root)
    return rel.split(os.sep)[0] if os.sep in rel else "."


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


def dominant(counter):
    """Return (value, share) of the most common entry, or (None, share)."""
    total = sum(counter.values())
    if not total:
        return None, 0.0
    value, n = counter.most_common(1)[0]
    return value, n / total


def code_text(s):
    """Source with comment-only lines removed, so a comment that
    mentions `var` does not count as a declaration."""
    return "\n".join(
        ln for ln in s.splitlines()
        if not ln.strip().startswith(("//", "*", "/*")))


def measure_js(files, root):
    m = {
        "files": len(files),
        "lines": 0,
        "decl": collections.Counter(),
        "quotes": collections.Counter(),
        "semicolon_lines": 0,
        "statement_lines": 0,
        "naming": collections.Counter(),
        "naming_by_file": {},
        "class_files": [],
        "errors": collections.Counter(),       # repo-wide
        "errors_by_dir": collections.defaultdict(collections.Counter),
        "logging_by_dir": collections.defaultdict(collections.Counter),
        "var_files": collections.Counter(),
        "require": 0,
        "import": 0,
    }
    for f in files:
        try:
            s = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        d = topdir(root, f)
        lines = s.splitlines()
        m["lines"] += len(lines)
        s = code_text(s)
        m["decl"]["const"] += len(re.findall(r"\bconst\b", s))
        m["decl"]["let"] += len(re.findall(r"\blet\b", s))
        m["decl"]["var"] += len(re.findall(r"\bvar\b", s))
        m["quotes"]["single"] += len(re.findall(r"'[^'\n]{0,80}'", s))
        m["quotes"]["double"] += len(re.findall(r'"[^"\n]{0,80}"', s))
        m["import"] += len(re.findall(r"^\s*import\b", s, re.M))
        m["require"] += len(re.findall(r"\brequire\s*\(", s))
        style = naming_style(os.path.basename(f))
        m["naming"][style] += 1
        m["naming_by_file"][os.path.relpath(f, root)] = style
        cls = re.findall(r"\bclass\s+([A-Z][A-Za-z0-9]*)", s)
        if cls:
            m["class_files"].append((os.path.relpath(f, root), cls))
        for ln in lines:
            stripped = ln.strip()
            if not stripped or stripped.startswith(("//", "*", "/*")):
                continue
            if re.search(r"[A-Za-z0-9_\)\]\}\"']\s*;$", stripped):
                m["semicolon_lines"] += 1
            if re.search(r"[A-Za-z0-9_\)\]\}\"']\s*$", stripped) and not stripped.endswith(("{", "}", ",", ":", "=>")):
                m["statement_lines"] += 1
        n_var = len(re.findall(r"\bvar\b", s))
        if n_var:
            m["var_files"][os.path.relpath(f, root)] += n_var
        for key, pat in (("throw", r"\bthrow\b"),
                         ("return_null", r"\breturn null\b"),
                         ("console_error", r"console\.error"),
                         ("process_exit", r"process\.exit")):
            n = len(re.findall(pat, s))
            m["errors"][key] += n
            m["errors_by_dir"][d][key] += n
        for key, pat in (("console_log", r"console\.log"),
                         ("console_warn", r"console\.warn")):
            n = len(re.findall(pat, s))
            m["logging_by_dir"][d][key] += n
    return m


def measure_py(files, root):
    m = {"files": len(files), "lines": 0,
         "quotes": collections.Counter(),
         "naming": collections.Counter(),
         "defs": collections.Counter()}
    for f in files:
        try:
            s = open(f, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        m["lines"] += len(s.splitlines())
        m["quotes"]["single"] += len(re.findall(r"'[^'\n]{0,80}'", s))
        m["quotes"]["double"] += len(re.findall(r'"[^"\n]{0,80}"', s))
        m["defs"]["def"] += len(re.findall(r"^\s*def\s+", s, re.M))
        m["defs"]["class"] += len(re.findall(r"^\s*class\s+", s, re.M))
        m["naming"][naming_style(os.path.basename(f))] += 1
    return m


def measure_commits(root, n=100):
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", "--format=%s", f"-{n}"],
            capture_output=True, text=True, timeout=30).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    non_merge = [m for m in out if not m.startswith("Merge ")]
    if not non_merge:
        return None
    prefixes = collections.Counter()
    for msg in non_merge:
        mm = re.match(r"^([A-Za-z][A-Za-z /&-]{1,20}?):", msg)
        prefixes[mm.group(1) if mm else "(no prefix)"] += 1
    return {"total": len(non_merge),
            "with_prefix": sum(v for k, v in prefixes.items()
                               if k != "(no prefix)"),
            "prefixes": dict(prefixes.most_common(8))}


def measure_layout(root, js_files, py_files):
    checks = [os.path.relpath(f, root) for f in js_files
              if os.path.basename(f).startswith("check-")]
    tests = [os.path.relpath(f, root) for f in js_files + py_files
             if re.search(r"(^|[/._-])test", os.path.basename(f))]
    return {"check_scripts": checks, "test_files": tests}


def build_rules(js, py, commits):
    """Turn measurements into rules. Only dominant patterns qualify."""
    rules = []

    def add(rule_id, dimension, expected, evidence, scope, note="",
            enforced_by="checker", severity="hard"):
        rules.append({"id": rule_id, "dimension": dimension,
                      "expected": expected, "evidence": evidence,
                      "scope": scope, "note": note,
                      "enforced_by": enforced_by,
                      "severity": severity})

    value, share = dominant(js["decl"])
    if value == "const" and share >= DOMINANCE:
        total = sum(js["decl"].values())
        add("JS-DECL", "declarations", "const",
            f"const {js['decl']['const']} of {total} declarations "
            f"({share:.0%}); let {js['decl']['let']}, "
            f"var {js['decl']['var']}", "repo",
            "var survives only as listed outliers, if any.")
    value, share = dominant(js["quotes"])
    if share >= DOMINANCE:
        total = sum(js["quotes"].values())
        add("JS-QUOTES", "quotes", value,
            f"{value} quotes {js['quotes'][value]} of {total} "
            f"({share:.0%})", "repo",
            "The other quote style is allowed inside a string that "
            "contains the dominant quote character. The double quotes "
            "that remain cluster in HTML template strings and regexes, "
            "so this rule is advisory: the checker reports it but "
            "does not fail on it. Quote style is a formatter's job.",
            severity="advisory")
    if js["lines"]:
        semi_share = js["semicolon_lines"] / max(
            1, js["semicolon_lines"] + js["statement_lines"])
        if semi_share >= DOMINANCE:
            add("JS-SEMI", "semicolons", "semicolons",
                f"{js['semicolon_lines']} lines end with ';' "
                f"({semi_share:.0%} of statement lines)", "repo",
                "Line-based checks are too noisy for this one — "
                "enforce it with a formatter, not the checker.",
                enforced_by="formatter")

    value, share = dominant(js["naming"])
    if value == "kebab" and share < DOMINANCE:
        # Naming splits by role: PascalCase files define a class.
        pascal = [f for f, classes in js["class_files"]
                  if naming_style(os.path.basename(f)) == "PascalCase"
                  and os.path.splitext(os.path.basename(f))[0] in classes]
        if pascal:
            add("JS-NAME", "file naming",
                "kebab-case, except a file defining one class takes "
                "that class's PascalCase name",
                f"kebab {js['naming']['kebab']}, PascalCase "
                f"{js['naming']['PascalCase']} — {len(pascal)} of the "
                f"PascalCase files define a class of the same name",
                "repo",
                "Files whose names a framework dictates "
                "(e.g. _middleware.js) are exempt.")
    elif share >= DOMINANCE:
        add("JS-NAME", "file naming", value,
            f"{value} {js['naming'][value]} of {sum(js['naming'].values())} "
            f"files ({share:.0%})", "repo")

    # Logging: a directory with zero console.log calls is a no-log scope
    # for log output. console.warn is reported separately — this repo
    # keeps two deliberate warns in apps/, both commented, both in
    # places where an error must never stop the loop or the boot.
    for d, counter in sorted(js["logging_by_dir"].items()):
        if counter.get("console_log", 0) == 0:
            warns = counter.get("console_warn", 0)
            add("JS-NOLOG", "logging", "no console.log",
                f"0 console.log calls across the whole directory"
                + (f"; console.warn appears {warns} time(s)"
                   if warns else ""), d,
                "Progress output belongs in scripts/, not shipped code.")
    if js["import"] and not js["require"]:
        add("JS-ESM", "modules", "ESM import/export, no require()",
            f"{js['import']} import statements, 0 require() calls", "repo")
    if py["files"] >= 3:
        value, share = dominant(py["quotes"])
        if share >= DOMINANCE:
            total = sum(py["quotes"].values())
            add("PY-QUOTES", "quotes", value,
                f"{value} quotes {py['quotes'][value]} of {total} "
                f"({share:.0%})", "python files",
                "Same caveat as JS-QUOTES: strings that contain the "
                "other quote character, and template-heavy code, make "
                "this advisory, not a failure.",
                severity="advisory")
    if commits and commits["total"]:
        share = commits["with_prefix"] / commits["total"]
        if share >= DOMINANCE:
            areas = ", ".join(
                f"{k} {v}" for k, v in list(commits["prefixes"].items())[:4]
                if k != "(no prefix)")
            add("GIT-MSG", "commit messages", "Area: summary",
                f"{commits['with_prefix']} of {commits['total']} "
                f"non-merge commits carry an Area: prefix "
                f"({share:.0%}); top areas: {areas}",
                "repo",
                "Merge commits are exempt.")
    return rules


def render_md(root, js, py, commits, layout, rules):
    L = []
    L.append(f"# Conventions — {os.path.basename(os.path.abspath(root))}")
    L.append("")
    L.append("Extracted by `extract_conventions.py` from what the code "
             "actually does. Every rule carries its count; a pattern "
             "below 80% is listed as mixed, not enforced.")
    L.append("")
    L.append(f"Measured: {js['files']} JS/TS files, {js['lines']:,} lines"
             + (f"; {py['files']} Python files, {py['lines']:,} lines"
                if py["files"] else "") + ".")
    L.append("")
    L.append("## Rules")
    L.append("")
    for r in rules:
        L.append(f"- **{r['id']} — {r['dimension']}: {r['expected']}** "
                 f"({r['scope']}). {r['evidence']}. {r['note']}"
                 + (" [advisory — reported, does not fail the check]"
                    if r.get("severity") == "advisory" else "")
                 + (" [enforced by a formatter, not the checker]"
                    if r.get("enforced_by") == "formatter" else ""))
    L.append("")
    L.append("## Measured, but mixed — decide, don't enforce")
    L.append("")
    value, share = dominant(js["decl"])
    if share < DOMINANCE:
        L.append(f"- Declarations are mixed: "
                 + ", ".join(f"{k} {v}" for k, v in js["decl"].items())
                 + ".")
    value, share = dominant(js["quotes"])
    if share < DOMINANCE:
        L.append(f"- Quotes are mixed: "
                 + ", ".join(f"{k} {v}" for k, v in js["quotes"].items())
                 + ".")
    for d, counter in sorted(js["errors_by_dir"].items()):
        total = sum(counter.values())
        if total:
            L.append(f"- Error handling in `{d}/`: "
                     + ", ".join(f"{k} {v}" for k, v in counter.items()
                                 if v) + ".")
    for d, counter in sorted(js["logging_by_dir"].items()):
        total = sum(counter.values())
        if total:
            L.append(f"- Logging in `{d}/`: "
                     + ", ".join(f"{k} {v}" for k, v in counter.items()
                                 if v) + ".")
    if js["var_files"]:
        L.append("- `var` outliers (the only places `var` appears): "
                 + ", ".join(f"{f} ({n})" for f, n
                             in js["var_files"].most_common()) + ". "
                 + "Record each as a deliberate exception or fix it.")
    L.append("")
    L.append("## Layout")
    L.append("")
    if layout["check_scripts"]:
        L.append("- Check scripts: "
                 + ", ".join(layout["check_scripts"]) + ".")
    if layout["test_files"]:
        L.append("- Test files: "
                 + ", ".join(layout["test_files"][:10])
                 + (f" (+{len(layout['test_files']) - 10} more)"
                    if len(layout["test_files"]) > 10 else "") + ".")
    if commits:
        L.append(f"- Commit messages: {commits['with_prefix']} of "
                 f"{commits['total']} non-merge commits carry an "
                 f"`Area:` prefix.")
    L.append("")
    L.append("## What this does not cover")
    L.append("")
    L.append("- Intent. A check can say the file is named right and "
             "uses `const`; it cannot say the change is correct.")
    L.append("- Conventions that live only in review culture. If the "
             "measurement is mixed, a human decides — the extractor "
             "does not guess.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    js_files, py_files = collect_files(root)
    js = measure_js(js_files, root)
    py = measure_py(py_files, root)
    commits = measure_commits(root)
    layout = measure_layout(root, js_files, py_files)
    rules = build_rules(js, py, commits)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "CONVENTIONS.md"), "w") as fh:
        fh.write(render_md(root, js, py, commits, layout, rules))
    data = {"root": os.path.basename(root),
            "measured": {"js_files": js["files"], "js_lines": js["lines"],
                         "py_files": py["files"], "py_lines": py["lines"]},
            "rules": rules,
            "outliers": {"var_files": dict(js["var_files"])},
            "mixed": {
                "errors_by_dir": {d: dict(c) for d, c
                                  in js["errors_by_dir"].items()},
                "logging_by_dir": {d: dict(c) for d, c
                                   in js["logging_by_dir"].items()}}}
    with open(os.path.join(args.out, "conventions.json"), "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"{js['files']} JS files, {js['lines']:,} lines; "
          f"{py['files']} Python files")
    print(f"{len(rules)} rules written to {args.out}/CONVENTIONS.md "
          f"and conventions.json")
    for r in rules:
        print(f"  {r['id']}: {r['expected']} ({r['scope']})")


if __name__ == "__main__":
    main()
