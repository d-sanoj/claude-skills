#!/usr/bin/env python3
"""triage-log.py — find the first real error in a failing build/test log.

Usage:  python3 triage-log.py <logfile> [--json]

The mistake this fixes: reading a log bottom-up. The last line of a failed
run is almost never the cause — it is the exit code, the summary count, or
the last consequence of a failure that started much earlier. Three rules:

1. The FIRST real error is the cause; everything after it is cascade
   until proven otherwise.
2. A traceback is one unit, and its cause is its LAST line (the
   exception), not its first ("Traceback (most recent call last):" says
   nothing). pytest's short tracebacks work the same way: the `E` line
   and the `file:line: Exception` line at the end are the cause.
3. Summaries are not causes. "Found 2 errors.", "Process completed
   with exit code 1.", "npm error Usage: ..." and warning noise name
   nothing — skip them. If a failing step contains no error line at
   all, the cause is the step's last substantive line (the process's
   last words before it died).

Output is a short verdict: the root-cause line, the file:line, the
failing command/step, how often the same error repeats, and a
classification (defect / config / environment / unknown).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field

# Real ESC bytes and gh's caret rendering of them ("^[[36;1m").
ANSI = re.compile(r"(?:\x1b|\^)\[[0-9;]*[A-Za-z]")
# GitHub Actions log lines: "CI\t<Step>\t<timestamp> <message>"
# (a BOM sometimes sits between the tab and the timestamp).
GH_PREFIX = re.compile(r"^[^\t]*\t([^\t]+)\t\ufeff?\d{4}-\d{2}-\d{2}T\S+\s?(.*)$")
# Longest extensions first, so "package.json" is not read as "package.js".
FILE_LINE = re.compile(
    r"([\w./\\-]+?\.(?:json|jsx|tsx|yaml|yml|toml|lock|txt|sh|py|js|ts|md)"
    r"(?::\d+(?::\d+)?)?)(?!(?::\d)|[\w.])"
)
FAIL_WORD = re.compile(
    r"error|fail|exception|traceback|was not found|not found at|"
    r"no such file|cannot find|missing|undefined|invalid|unsatisf|"
    r"denied|refused|timeout|timed out|killed|aborted|panic|fatal|crash",
    re.IGNORECASE,
)
# The exception line of a failure: "ModuleNotFoundError: ...",
# "file:line: AssertionError", "error: Library stubs ...".
EXCEPTION_LINE = re.compile(r"\b\w*(error|exception)\b", re.IGNORECASE)
# Lines that look alarming but name no cause — consequences, summaries, help.
NOISE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"##\[error\]process completed with exit code",
        r"^found \d+ errors?\.?$",
        r"^found \d+ error in \d+ files?",
        r"npm error (usage|options|aliases|run \"npm help)",
        r"^npm error \[--",
        r"^npm error npm ci$",
        r"a complete log of this run can be found in",
        r"deprecat",
        r"^npm warn",
        r"^\s*warning:",
        r"^\s*note: ",
        r"^\s*=\s*help:",
        r"^\s*\|\s*$",
        r"^ok\s+",
        r"\bPASSED\b",
        r"^\s*\.\s*$",
    ]
]
DIAGNOSTIC = re.compile(
    r"^[\w./\\-]+\.\w+:\d+:\d+: [A-Z]+\d+\b"  # ruff/mypy style: file:line:col: CODE
    r"|^[\w./\\-]+\.\w+:\d+: error:"  # mypy/gcc style: file:line: error:
    r"|^[\w./\\-]+\.\w+:\d+: \w*(Error|Exception|Warning)\b"  # pytest: file:line: AssertionError
)
TRACEBACK_START = re.compile(r"^\s*Traceback \(most recent call last\):\s*$")
SECTION = re.compile(
    r"^(=+|_+|-{3,})\s*(FAILURES|ERRORS|WARNINGS|short test summary)?"
)
EXIT_LINE = re.compile(r"process completed with exit code|exit code 1", re.IGNORECASE)
COMMAND = re.compile(r"^(?:Run |\$ )(.+)$")


@dataclass
class Finding:
    cause: str
    file_line: str | None
    step: str | None
    command: str | None
    repeats: int
    classification: str
    evidence: list[str] = field(default_factory=list)


def strip_ansi(line: str) -> str:
    return ANSI.sub("", line)


def split_gh(line: str) -> tuple[str | None, str]:
    """Return (step, message) for a GitHub Actions log line, else (None, line)."""
    m = GH_PREFIX.match(line)
    if m:
        return m.group(1), m.group(2)
    return None, line


def is_noise(text: str) -> bool:
    return any(p.search(text) for p in NOISE)


def is_error_line(text: str) -> bool:
    if is_noise(text):
        return False
    return bool(FAIL_WORD.search(text) or DIAGNOSTIC.match(text))


def specificity(text: str) -> int:
    """How concretely a line names the cause: paths, versions, quoted names."""
    score = 0
    if FILE_LINE.search(text):
        score += 2
    if re.search(r"[\w@./-]+@\d", text):  # package@version
        score += 2
    if '"' in text or "'" in text:
        score += 1
    if re.search(r"\bline \d+\b", text, re.IGNORECASE):
        score += 1
    if re.search(r"^(npm error code|error:|Error:)\s+\w+$", text.strip()):
        score -= 1  # a bare code names nothing on its own
    return score


def pick_cause(block_lines: list[str]) -> str:
    """The most informative failure line in a block.

    Prefer the exception line itself ("ModuleNotFoundError: ...",
    "file:line: AssertionError") over a header that merely contains
    the word FAIL; among equals, the most specific line wins, then
    the earliest.
    """
    candidates = [ln for ln in block_lines if is_error_line(ln)]
    if not candidates:
        return block_lines[0]
    preferred = [ln for ln in candidates if EXCEPTION_LINE.search(ln) and ":" in ln]
    pool = preferred or candidates
    best = max(pool, key=lambda ln: (specificity(ln), -pool.index(ln)))
    return best


def classify(cause: str) -> str:
    text = cause.lower()
    if re.search(
        r"\bchrome\b|\bport\b|\bnetwork\b|\bconnection\b|\bregistry\b|"
        r"\btimeout\b|timed out|\bdisk\b|no space|eai_again|etarget|econnrefused",
        text,
    ):
        return "environment"
    if re.search(
        r"lock file|stubs not installed|was not found|not found at|"
        r"missing:|cannot find|eusage|does not satisfy|no module named",
        text,
    ):
        return "config"
    return "defect"


def triage(lines: list[str]) -> Finding:
    """Find the first real error in the log."""
    parsed: list[tuple[str | None, str]] = []
    for raw in lines:
        line = strip_ansi(raw).rstrip("\n")
        step, message = split_gh(line)
        parsed.append((step, message))

    last_command: str | None = None
    last_step: str | None = None

    # Group lines into blocks: a block starts at an error-looking line or a
    # traceback start. A block ends at a section header or after 12 lines —
    # blank lines do not end one, because stack traces have blank lines in
    # them (the source excerpt, then a blank, then the SyntaxError).
    blocks: list[dict] = []
    current: dict | None = None
    in_traceback = False

    def flush() -> None:
        nonlocal current
        if current is not None:
            blocks.append(current)
            current = None

    for idx, (step, message) in enumerate(parsed):
        if step:
            last_step = step
        cmd = COMMAND.match(message)
        if cmd:
            last_command = cmd.group(1).strip() or last_command
        if re.match(r"^> [\w@./-]+@[\d.]+ ", message):
            # npm's echo of the script ("npm run build:dist"), not the command.
            pass
        elif re.match(r"^> \S", message):
            # A shell command echoed as "> <cmd>"; pytest's ">" source lines
            # have spaces after "> ", so they do not match.
            last_command = message[2:].strip()
        text = message.strip()
        if not text:
            continue
        if SECTION.match(text):
            # Structural header, never an error itself. It ends any open block.
            in_traceback = False
            flush()
            continue
        if TRACEBACK_START.match(text):
            in_traceback = True
            if current is None:
                current = {"lines": [], "step": last_step, "command": last_command,
                           "start": idx}
            current["lines"].append(text)
            continue
        if in_traceback:
            current["lines"].append(text)
            if len(current["lines"]) > 12:
                in_traceback = False
                flush()
            continue
        if is_error_line(text):
            if current is None:
                current = {"lines": [], "step": last_step, "command": last_command,
                           "start": idx}
            current["lines"].append(text)
            continue
        if current is not None:
            # Context lines inside a block (source excerpts, stack frames).
            current["lines"].append(text)
            if len(current["lines"]) > 12:
                flush()
    flush()

    for block in blocks:
        block_lines = block["lines"]
        cause = pick_cause(block_lines)
        # file:line — from the cause line first; otherwise the shortest
        # match in the block and the 5 lines before it (Node prints the
        # file:line above the source excerpt, pytest the relative path).
        file_line = None
        m = FILE_LINE.search(cause)
        if m:
            file_line = m.group(1)
        else:
            candidates: list[str] = []
            for _, msg in parsed[max(0, block["start"] - 5):block["start"]]:
                candidates += [mm.group(1) for mm in FILE_LINE.finditer(msg)]
            for ln in block_lines:
                candidates += [mm.group(1) for mm in FILE_LINE.finditer(ln)]
            if candidates:
                # Prefer a match with a line number; then the shortest.
                file_line = min(
                    candidates,
                    key=lambda c: (0 if re.search(r":\d+", c) else 1, len(c)),
                )
        if file_line:
            # Node prints file:// URLs; collapse the leading slashes.
            file_line = re.sub(r"^/+", "/", file_line)
        norm = re.sub(r"\s+", " ", cause).strip().lower()
        repeats = sum(
            1
            for _, msg in parsed
            if re.sub(r"\s+", " ", msg).strip().lower() == norm
        )
        return Finding(
            cause=cause.strip(),
            file_line=file_line,
            step=block["step"],
            command=block["command"],
            repeats=repeats,
            classification=classify(cause),
            evidence=[ln.strip() for ln in block_lines[:6]],
        )

    # No error line anywhere: the cause is the last substantive line
    # before the exit-code line — the process's last words before it died.
    # (Everything after the exit line is post-job cleanup.)
    cutoff = len(parsed)
    for i, (_, msg) in enumerate(parsed):
        if EXIT_LINE.search(msg):
            cutoff = i
            break
    substantive = [
        (step, msg.strip())
        for step, msg in parsed[:cutoff]
        if msg.strip()
        and not is_noise(msg.strip())
        and not msg.strip().startswith("##[")
        and not re.match(r"^\[command\]", msg.strip())
    ]
    if substantive:
        step, last = substantive[-1]
        file_match = FILE_LINE.search(last)
        return Finding(
            cause=last,
            file_line=file_match.group(1) if file_match else None,
            step=step or last_step,
            command=last_command,
            repeats=1,
            classification=classify(last),
            evidence=[last],
        )
    return Finding(
        cause="(no error line found; the log may be truncated)",
        file_line=None,
        step=last_step,
        command=last_command,
        repeats=0,
        classification="unknown",
        evidence=[],
    )


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    if not args:
        print("usage: triage-log.py <logfile> [--json]", file=sys.stderr)
        return 2
    with open(args[0], encoding="utf-8", errors="replace") as fh:
        finding = triage(fh.readlines())
    if as_json:
        print(json.dumps(finding.__dict__, indent=2))
        return 0
    print(f"ROOT CAUSE: {finding.cause}")
    if finding.file_line:
        print(f"FILE:       {finding.file_line}")
    if finding.step:
        print(f"STEP:       {finding.step}")
    if finding.command:
        print(f"COMMAND:    {finding.command}")
    if finding.repeats > 1:
        print(f"REPEATS:    same error {finding.repeats}x in this log")
    print(f"CLASS:      {finding.classification}")
    print("NEXT:       " + {
        "defect": "reproduce it locally, fix the smallest cause, rerun the same command.",
        "config": "fix the config/dependency, then rerun — do not touch the code.",
        "environment": "rerun first: if it passes, it was the environment, not your change.",
        "unknown": "the log names no cause — get the full log before guessing.",
    }[finding.classification])
    if finding.evidence:
        print("EVIDENCE:")
        for line in finding.evidence:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
