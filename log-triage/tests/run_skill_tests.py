#!/usr/bin/env python3
"""Tests for log-triage. Run from the skill folder:
  python3 tests/run_skill_tests.py
No packages, no network. Exit 0 when all pass.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SCRIPT = SKILL / "scripts" / "triage-log.py"

spec = importlib.util.spec_from_file_location("triage_log", SCRIPT)
triage_log = importlib.util.module_from_spec(spec)
sys.modules["triage_log"] = triage_log
spec.loader.exec_module(triage_log)

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def triage(text):
    return triage_log.triage(text.splitlines())


# R4: a step with no error word — the cause is the step's last line.
CHROME = """CI\tBuild\t2026-11-17T17:21:04.3098930Z Measuring the plain page for the sine layout...
CI\tBuild\t2026-11-17T17:21:24.3824096Z Chrome did not open a debugging port
CI\tBuild\t2026-11-17T17:21:24.3989741Z ##[error]Process completed with exit code 1.
CI\tPost Checkout\t2026-11-17T17:21:24.4138302Z Post job cleanup.
"""
f = triage(CHROME)
check("R4 chrome-port cause", f.cause == "Chrome did not open a debugging port", f.cause)
check("R4 chrome-port class", f.classification == "environment", f.classification)
check("R4 chrome-port step", f.step == "Build", str(f.step))
check("R4 no post-cleanup leak", "cleanup" not in f.cause.lower(), f.cause)

# R2: a traceback is one unit; the cause is its last line.
TRACEBACK = """=================================== FAILURES ===================================
______________________ test_bm25_ranks_matching_doc_first ______________________

    def test_bm25_ranks_matching_doc_first():
        chunks = _chunks()
        scores = BM25(chunks).scores(tokenize("cat sat"))
>       assert scores[0] < scores[1]
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert np.float64(1.4508328822574619) < np.float64(0.4700036292457356)

tests/test_scorers.py:38: AssertionError
"""
f = triage(TRACEBACK)
check("R2 traceback cause", f.cause == "tests/test_scorers.py:38: AssertionError", f.cause)
check("R2 traceback file", f.file_line == "tests/test_scorers.py:38", str(f.file_line))
check("R2 traceback class", f.classification == "defect", f.classification)

# R3: summaries name nothing — the cause is the first diagnostic, not "Found 2 errors."
RUFF = """messy.py:2:8: F401 [*] `os` imported but unused
  |
1 | \"\"\"A file with real lint violations.\"\"\"
2 | import os  # unused
  |        ^^ F401
  |
  = help: Remove unused import: `os`

messy.py:6:22: F821 Undefined name `undefined_name`

Found 2 errors.
[*] 1 fixable with the `--fix` option.
"""
f = triage(RUFF)
check("R3 ruff cause", f.cause == "messy.py:2:8: F401 [*] `os` imported but unused", f.cause)
check("R3 ruff file", f.file_line == "messy.py:2:8", str(f.file_line))

# R1+R5: 25 lines of the same pattern are one failure; the first names the package.
NPM = """npm error code EUSAGE
npm error
npm error `npm ci` can only install packages when your package.json and package-lock.json or npm-shrinkwrap.json are in sync. Please update your lock file with `npm install` before continuing.
npm error
npm error Invalid: lock file's esbuild@99.99.99 does not satisfy esbuild@0.24.2
npm error Invalid: lock file's @esbuild/aix-ppc64@99.99.99 does not satisfy @esbuild/aix-ppc64@0.24.2
npm error Invalid: lock file's @esbuild/android-arm@99.99.99 does not satisfy @esbuild/android-arm@0.24.2
npm error
npm error A complete log of this run can be found in: /home/u/.npm/_logs/2026-11-21-debug-0.log
"""
f = triage(NPM)
check("R1 npm cause", f.cause == "npm error Invalid: lock file's esbuild@99.99.99 does not satisfy esbuild@0.24.2", f.cause)
check("R1 npm class", f.classification == "config", f.classification)

# R3: the first "error" match can be a line of source code — the script
# must not take it; the SyntaxError line below it is the cause.
NODE = """
> sine-portfolio@1.0.0 build:dist
> node scripts/build.js --dist

file:///tmp/repro/scripts/build.js:13
const broken = ; // stray semicolon
               ^

SyntaxError: Unexpected token ';'
    at compileSourceTextModule (node:internal/modules/esm/utils:319:16)

Node.js v24.22.1
"""
f = triage(NODE)
check("R3 node cause", f.cause == "SyntaxError: Unexpected token ';'", f.cause)
check("R3 node file", f.file_line is not None and f.file_line.endswith("scripts/build.js:13"), str(f.file_line))
check("R3 node not source line", "const broken" not in f.cause, f.cause)
check("R6 node command", f.command == "node scripts/build.js --dist", str(f.command))

# R5: the same error printed twice counts as one cause with repeats == 2.
COVER = """FAIL  post links, dates and posters
BlogError: content/blog/blog-17-11-18-2026/chunk-by-section-not-by-word-count.md: image "img/cover.png" was not found at content/blog/blog-17-11-18-2026/img/cover.png
FAIL  build writes pages, posters and feed
BlogError: content/blog/blog-17-11-18-2026/chunk-by-section-not-by-word-count.md: image "img/cover.png" was not found at content/blog/blog-17-11-18-2026/img/cover.png
"""
f = triage(COVER)
check("R5 repeats counted", f.repeats == 2, str(f.repeats))
check("R5 repeats cause", "cover.png" in f.cause and "was not found" in f.cause, f.cause)

# R5: a missing-stubs error repeats in the hint lines, not as a repeat.
MYPY = """check_yaml.py:3: error: Library stubs not installed for "yaml"  [import-untyped]
check_yaml.py:3: note: Hint: "python3 -m pip install types-PyYAML"
Found 1 error in 1 file (checked 1 source file)
"""
f = triage(MYPY)
check("mypy stubs cause", f.cause.startswith('check_yaml.py:3: error: Library stubs'), f.cause)
check("mypy stubs class", f.classification == "config", f.classification)

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {', '.join(FAILURES)}")
    sys.exit(1)
print("all tests pass")
