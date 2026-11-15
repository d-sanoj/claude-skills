#!/usr/bin/env python3
"""End-to-end tests for convention-check. No model, no network.

Builds a small fixture repo in a temp directory (three good files,
two bad ones and one advisory-only file, two Area:-prefixed commits), runs the extractor and
the checker, and asserts the exact numbers the skill promises:

- the extractor finds the const / single-quote / naming / no-log /
  commit-message rules on the good files;
- the checker is clean on the good files (exit 0);
- bad-service.js fails with exactly 2 JS-DECL + 1 JS-NOLOG hard
  violations and 1 advisory quote note;
- DateHelpers.js fails with exactly 1 JS-NAME violation;
- ok-but-quoted.js passes (exit 0) with 1 advisory note;
- a commit message without an Area: prefix fails, one with it passes.

Run: python3 tests/run_skill_tests.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
EXTRACT = os.path.join(SKILL, "scripts", "extract_conventions.py")
CHECK = os.path.join(SKILL, "scripts", "check_conventions.py")
FIXTURES = os.path.join(SKILL, "examples", "fixtures")

GOOD_WIDGET = """// A well-behaved widget file.
export const widgetName = 'good-widget';

export function render(name) {
  const label = 'widget: ' + name;
  return label;
}
"""

GOOD_CLASS = """// A PascalCase file that earns its name: it defines class Widget.
export class Widget {
  constructor(name) {
    this.name = name;
  }

  render() {
    return 'widget: ' + this.name;
  }
}
"""

GOOD_SCRIPT = """// Scripts may log progress; shipped code may not.
console.log('building the widget');
"""

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name
          + (f" — {detail}" if detail and not cond else ""))


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=60)


def main():
    tmp = tempfile.mkdtemp(prefix="convention-check-test-")
    try:
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, "apps"))
        os.makedirs(os.path.join(repo, "scripts"))
        files = {
            "apps/good-widget.js": GOOD_WIDGET,
            "apps/Widget.js": GOOD_CLASS,
            "scripts/run.js": GOOD_SCRIPT,
        }
        for rel, text in files.items():
            with open(os.path.join(repo, rel), "w") as fh:
                fh.write(text)
        run(["git", "init", "-q"], repo)
        run(["git", "config", "user.email", "test@example.com"], repo)
        run(["git", "config", "user.name", "Test"], repo)
        run(["git", "add", "."], repo)
        run(["git", "commit", "-qm", "Setup: initial files"], repo)
        run(["git", "commit", "-qm", "Widget: add widget",
             "--allow-empty"], repo)

        out = os.path.join(tmp, "out")
        r = run([sys.executable, EXTRACT, "--root", repo, "--out", out],
                repo)
        check("extractor exits 0", r.returncode == 0, r.stderr[-300:])
        with open(os.path.join(out, "conventions.json")) as fh:
            data = json.load(fh)
        ids = {rule["id"] for rule in data["rules"]}
        for rid in ("JS-DECL", "JS-QUOTES", "JS-NAME", "JS-NOLOG",
                    "GIT-MSG"):
            check(f"extractor finds {rid}", rid in ids,
                  f"found: {sorted(ids)}")
        nolog = [rule for rule in data["rules"]
                 if rule["id"] == "JS-NOLOG"]
        check("no-log scope is apps/",
              any(rule["scope"] == "apps" for rule in nolog),
              f"scopes: {[rule['scope'] for rule in nolog]}")
        check("no-log scope is NOT scripts/",
              not any(rule["scope"] == "scripts" for rule in nolog))

        # The bad files arrive after extraction — this is the real
        # workflow: extract the conventions from the repo as it
        # stands, then check the new diff against them.
        for name in ("bad-service.js", "DateHelpers.js",
                     "ok-but-quoted.js"):
            shutil.copy(os.path.join(FIXTURES, name),
                        os.path.join(repo, "apps", name))

        rules = os.path.join(out, "conventions.json")
        good = ["apps/good-widget.js", "apps/Widget.js",
                "scripts/run.js"]
        r = run([sys.executable, CHECK, "--rules", rules, "--root", "."] + good, repo)
        check("checker clean on good files", r.returncode == 0,
              r.stdout[-400:])
        check("clean message names the file count",
              "3 file(s) checked" in r.stdout, r.stdout[-200:])

        r = run([sys.executable, CHECK, "--rules", rules, "--root", ".",
                 "apps/bad-service.js"], repo)
        check("bad-service.js fails", r.returncode == 1)
        check("bad-service.js: 2 JS-DECL",
              r.stdout.count("[JS-DECL]") == 2, r.stdout)
        check("bad-service.js: 1 JS-NOLOG",
              r.stdout.count("[JS-NOLOG]") == 1, r.stdout)
        check("bad-service.js: 1 advisory quote",
              r.stdout.count("[JS-QUOTES]") == 1, r.stdout)
        check("bad-service.js: summary says 3 in 1 file",
              "3 violation(s) in 1 file(s)" in r.stdout, r.stdout)

        r = run([sys.executable, CHECK, "--rules", rules, "--root", ".",
                 "apps/DateHelpers.js"], repo)
        check("DateHelpers.js fails", r.returncode == 1)
        check("DateHelpers.js: 1 JS-NAME",
              r.stdout.count("[JS-NAME]") == 1, r.stdout)

        r = run([sys.executable, CHECK, "--rules", rules, "--root", ".",
                 "apps/ok-but-quoted.js"], repo)
        check("ok-but-quoted.js passes (advisory only)",
              r.returncode == 0, r.stdout)
        check("ok-but-quoted.js: 1 advisory note",
              "1 advisory note(s)" in r.stdout, r.stdout)

        r = run([sys.executable, CHECK, "--rules", rules, "--root", ".",
                 "--check-commit-msg", "fixed the thing"], repo)
        check("bare commit message fails", r.returncode == 1)
        r = run([sys.executable, CHECK, "--rules", rules, "--root", ".",
                 "--check-commit-msg", "Widget: fixed the thing"], repo)
        check("Area:-prefixed commit message passes",
              r.returncode == 0, r.stdout)

        failed = [n for n, ok, _ in RESULTS if not ok]
        print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
        return 1 if failed else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
