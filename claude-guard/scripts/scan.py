#!/usr/bin/env python3
"""Scan Claude Code settings files for secrets saved by 'Don't Ask Again'.

Why this exists: when you approve a shell command in Claude Code with
"Yes, and don't ask again", Claude Code saves the exact command as an
allow rule in `.claude/settings.local.json`. If that command held a
password or key, the secret now sits in plain text in the project folder.
Apiiro (Nov 5, 2026) found 1,122 public copies of that file on GitHub
holding real secrets — and 215 of them were missed by both gitleaks and
TruffleHog, because a password typed inside a command (PGPASSWORD=...,
sshpass -p ...) does not look like a known key format.

This scanner looks for exactly the patterns those tools miss, and checks
whether each file is tracked by git, present in git history, and covered
by .gitignore — the three facts that decide whether a leak has happened.

Usage:
    python scan.py [PATH] [--json] [--transcripts] [--quiet]

PATH defaults to the current directory. Exit code 0 = no confirmed or
likely secret found, 1 = at least one confirmed or likely secret found,
2 = usage / scan error. Only "possible" findings still exit 0, with a
note telling you to review them by hand.

The scanner never contacts a host, never tries a credential, and never
prints a full secret value: values are shown redacted (first 4 chars,
an ellipsis, last 2 chars) so the report itself is safe to paste into
a ticket. All example secrets in this repo's tests are fake.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# --- secret patterns -------------------------------------------------
# (name, regex, severity, what it means)
# The regex must have the secret value in group 1 where one is marked.
KNOWN_FORMATS = [
    ("aws-access-key", r"\b(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16})\b",
     "confirmed", "AWS access key ID"),
    ("github-token", r"\b(ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}"
     r"|ghu_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|ghr_[A-Za-z0-9]{36}"
     r"|github_pat_[A-Za-z0-9_]{22,})\b",
     "confirmed", "GitHub personal access token"),
    ("npm-token", r"\b(npm_[A-Za-z0-9]{36})\b",
     "confirmed", "npm access token"),
    ("anthropic-key", r"\b(sk-ant-api03-[A-Za-z0-9_-]{20,}"
     r"|sk-ant-[A-Za-z0-9_-]{20,})\b",
     "confirmed", "Anthropic API key"),
    ("openai-key", r"\b(sk-[A-Za-z0-9]{20,})\b",
     "likely", "possible OpenAI-style API key (format alone is weak evidence)"),
    ("stripe-live-key", r"\b(sk_live_[A-Za-z0-9]{16,})\b",
     "confirmed", "Stripe live secret key"),
    ("slack-token", r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b",
     "confirmed", "Slack token"),
    ("private-key", r"-----BEGIN (?:[A-Z ]*)PRIVATE KEY-----",
     "confirmed", "private key material"),
    ("jwt", r"\b(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}"
     r"\.[A-Za-z0-9_-]{10,})\b",
     "likely", "JSON Web Token"),
    ("credential-url",
     r"[a-zA-Z][a-zA-Z0-9+.-]*://[^:/\s'\"]+:([^@/\s'\"]+)@",
     "confirmed", "password embedded in a URL (e.g. postgres://user:pass@host)"),
]

# Passwords typed into commands — the class gitleaks/TruffleHog miss.
# Group 1 is the secret value.
COMMAND_PASSWORDS = [
    ("pgpassword", r"\bPGPASSWORD\s*=\s*['\"]?([^\s'\";]+)",
     "likely", "database password in PGPASSWORD="),
    ("mysql-pwd", r"\bMYSQL_PWD\s*=\s*['\"]?([^\s'\";]+)",
     "likely", "database password in MYSQL_PWD="),
    ("sshpass", r"\bsshpass\s+-p\s+['\"]?([^\s'\"]+)",
     "likely", "password passed to sshpass -p"),
    ("mysql-p-flag", r"\bmysql\b[^'\"]*?\s-p([^\s'\"]{4,})",
     "likely", "password passed to mysql -p"),
    ("password-flag", r"--password[= ]['\"]?([^\s'\"]{4,})",
     "likely", "password passed as --password"),
    ("token-flag", r"--(?:api-?key|token)[= ]['\"]?([^\s'\"]{8,})",
     "likely", "token passed as --token/--api-key"),
    ("basic-auth-header",
     r"Authorization:\s*(?:Bearer|Basic)\s+([A-Za-z0-9+/=_.-]{8,})",
     "likely", "credential in an Authorization header"),
    ("curl-user", r"\bcurl\b[^'\"]*?\s-u\s+['\"]?([^\s'\":]+:[^\s'\"]+)",
     "likely", "username:password passed to curl -u"),
]

PLACEHOLDERS = {
    "", "***", "****", "*****", "your-password", "your_password",
    "changeme", "change-me", "example", "password", "secret",
    "test", "test123", "123456", "letmein", "admin", "xxx", "xxxx",
}
ENV_VAR = re.compile(r"^\$[A-Z_][A-Z0-9_]*$")

HIGH_ENTROPY = re.compile(r"[A-Za-z0-9+/=_-]{24,}")

SETTINGS_NAMES = ("settings.local.json", "settings.json")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
             "dist", "build", ".next", ".turbo", "target"}


def redact(value):
    """Show only the edges of a secret so reports stay safe to share."""
    if len(value) <= 6:
        return "*" * len(value)
    return value[:4] + "…" + value[-2:]


def looks_fake(value):
    low = value.lower()
    if "$" in value:
        # An environment-variable reference ($VAR or $USER:$PASS),
        # not a credential. This is the safe form the fixer suggests.
        return True
    if low in PLACEHOLDERS:
        return True
    if ENV_VAR.match(value):
        return True
    if low.startswith(("example", "test-", "fake-", "dummy", "xxx")):
        return True
    if set(low) <= set("x*_.-"):
        return True
    return False


def redact_text(text):
    """Replace every detected secret value in a string with •••, so
    rule text and locations can be shown without leaking the secret."""
    out = text
    for _name, pattern, _sev, _meaning in KNOWN_FORMATS + COMMAND_PASSWORDS:
        def repl(m):
            if m.lastindex:
                return m.group(0).replace(m.group(1), "•••", 1)
            return "•••"
        out = re.sub(pattern, repl, out)
    return out


def find_secrets(text, where):
    """Return a list of findings in one string of text."""
    findings = []
    for name, pattern, severity, meaning in KNOWN_FORMATS:
        for m in re.finditer(pattern, text):
            value = m.group(1) if m.lastindex else m.group(0)
            if looks_fake(value):
                continue
            findings.append({
                "class": name, "severity": severity, "meaning": meaning,
                "where": where, "value_preview": redact(value),
                "value_length": len(value),
            })
    for name, pattern, severity, meaning in COMMAND_PASSWORDS:
        for m in re.finditer(pattern, text):
            value = m.group(1)
            if looks_fake(value):
                continue
            findings.append({
                "class": name, "severity": severity, "meaning": meaning,
                "where": where, "value_preview": redact(value),
                "value_length": len(value),
            })
    # High-entropy strings that match no known format: possible only.
    # Only inside quoted values or after '=', to keep noise down.
    for m in re.finditer(r"[\"'=]([A-Za-z0-9+/=_-]{24,})[\"'\s,}]", text):
        value = m.group(1)
        if looks_fake(value):
            continue
        if any(f["value_preview"] == redact(value) for f in findings):
            continue
        if re.search(r"[a-z]", value) and re.search(r"[A-Z0-9]", value):
            findings.append({
                "class": "high-entropy", "severity": "possible",
                "meaning": "long mixed-case string; could be a token, "
                           "review by hand",
                "where": where, "value_preview": redact(value),
                "value_length": len(value),
            })
    return findings


def git(args, cwd):
    try:
        out = subprocess.run(["git"] + args, cwd=cwd,
                             capture_output=True, text=True, timeout=30)
        return out.returncode, out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, ""


def repo_root(path):
    code, out = git(["rev-parse", "--show-toplevel"],
                    os.path.dirname(os.path.abspath(path)))
    return out if code == 0 else None


def git_exposure(path):
    """tracked? in history? ignored? — the three facts that matter."""
    root = repo_root(path)
    if root is None:
        return {"in_git_repo": False}
    rel = os.path.relpath(os.path.abspath(path), root)
    code, _ = git(["ls-files", "--error-unmatch", "--", rel], root)
    tracked = code == 0
    code, log = git(["log", "--all", "--oneline", "--", rel], root)
    in_history = code == 0 and bool(log)
    history_commits = len(log.splitlines()) if in_history else 0
    code, _ = git(["check-ignore", "-q", "--", rel], root)
    ignored = code == 0
    return {
        "in_git_repo": True, "repo": root, "tracked": tracked,
        "in_history": in_history, "history_commits": history_commits,
        "ignored": ignored,
    }


def scan_settings_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        return {"path": path, "error": str(exc), "findings": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"path": path, "error": f"invalid JSON: {exc}",
                "findings": []}
    findings = []
    perms = data.get("permissions") or {}
    for section in ("allow", "deny", "ask"):
        for rule in perms.get(section) or []:
            if not isinstance(rule, str):
                continue
            for f in find_secrets(rule, f"permissions.{section}: {redact_text(rule[:80])}"):
                findings.append(f)
    for key, value in (data.get("env") or {}).items():
        if isinstance(value, str):
            for f in find_secrets(value, f"env.{key}"):
                findings.append(f)
    for hook_group in (data.get("hooks") or {}).values():
        groups = hook_group if isinstance(hook_group, list) else [hook_group]
        for group in groups:
            for hook in (group or {}).get("hooks") or []:
                cmd = (hook or {}).get("command", "")
                if isinstance(cmd, str) and cmd:
                    for f in find_secrets(cmd, f"hooks: {redact_text(cmd[:80])}"):
                        findings.append(f)
    # Anything else in the file that looks like a secret, keyed by path.
    for f in find_secrets(raw, "file body"):
        if not any(x["value_preview"] == f["value_preview"]
                   for x in findings):
            findings.append(f)
    return {"path": path, "findings": findings,
            "git": git_exposure(path)}


def find_settings_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if os.path.basename(dirpath) != ".claude":
            continue
        for name in filenames:
            if name in SETTINGS_NAMES:
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def find_transcripts(root):
    """Saved agent transcripts (.claude/projects/**/*.jsonl)."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if ".claude" not in dirpath.split(os.sep):
            continue
        for name in filenames:
            if name.endswith(".jsonl"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def scan_transcript(path):
    findings = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if i > 20000:
                    break
                for f in find_secrets(line, f"{path}:{i}"):
                    findings.append(f)
                    if len(findings) >= 20:
                        break
                if len(findings) >= 20:
                    break
    except OSError as exc:
        return {"path": path, "error": str(exc), "findings": []}
    return {"path": path, "findings": findings[:20],
            "git": git_exposure(path)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=".",
                    help="file or directory to scan (default: .)")
    ap.add_argument("--json", action="store_true",
                    help="emit machine-readable JSON")
    ap.add_argument("--transcripts", action="store_true",
                    help="also scan saved agent transcripts in .claude/projects")
    ap.add_argument("--quiet", action="store_true",
                    help="only print the summary line")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.path)
    if not (os.path.isfile(target) or os.path.isdir(target)):
        print(f"scan.py: no such file or directory: {args.path}",
              file=sys.stderr)
        return 2
    results = []
    if os.path.isfile(target):
        if target.endswith(".jsonl"):
            results.append(scan_transcript(target))
        else:
            results.append(scan_settings_file(target))
    else:
        for f in find_settings_files(target):
            results.append(scan_settings_file(f))
        if args.transcripts:
            for f in find_transcripts(target):
                results.append(scan_transcript(f))

    confirmed = sum(1 for r in results for f in r["findings"]
                    if f["severity"] in ("confirmed", "likely"))
    possible = sum(1 for r in results for f in r["findings"]
                   if f["severity"] == "possible")
    errors = [r for r in results if r.get("error")]

    if args.json:
        print(json.dumps({"results": results,
                          "summary": {"files_scanned": len(results),
                                      "confirmed_or_likely": confirmed,
                                      "possible": possible,
                                      "errors": len(errors)}},
                         indent=2))
    elif not args.quiet:
        if not results:
            print("No Claude Code settings files found under "
                  f"{args.path}.")
            print("Tip: run this in a project that uses Claude Code, "
                  "or pass a settings file directly.")
        for r in results:
            print(f"\n== {r['path']} ==")
            if r.get("error"):
                print(f"  ERROR: {r['error']}")
                continue
            g = r["git"]
            if g.get("in_git_repo"):
                print(f"  git: tracked={g['tracked']} "
                      f"in_history={g['in_history']} "
                      f"({g['history_commits']} commits) "
                      f"ignored={g['ignored']}")
                if g["tracked"]:
                    print("  !! This file is tracked by git. If the repo "
                          "is (or was) public, the secret is public.")
                if g["in_history"]:
                    print("  !! The file is in git history. Deleting it "
                          "now does not remove old copies.")
                if not g["ignored"] and not g["tracked"]:
                    print("  !! Not covered by .gitignore or global "
                          "excludes: one commit can publish it.")
            else:
                print("  git: not in a git repository")
            if not r["findings"]:
                print("  No secrets found.")
            for f in r["findings"]:
                print(f"  [{f['severity'].upper()}] {f['class']}: "
                      f"{f['meaning']}")
                print(f"      where: {f['where']}")
                print(f"      value: {f['value_preview']} "
                      f"({f['value_length']} chars)")
        print(f"\n{len(results)} file(s) scanned, "
              f"{confirmed} confirmed/likely secret(s), "
              f"{possible} possible (review by hand).")
        if confirmed:
            print("Rotate every secret above FIRST, then run "
                  "fix.py --apply to clean the files.")
        elif possible:
            print("No confirmed secret, but review the 'possible' items: "
                  "the scanner cannot tell a token from a long label.")
        if errors:
            print(f"{len(errors)} file(s) could not be read; "
                  "see ERROR lines above.")
    else:
        print(f"{len(results)} file(s), {confirmed} confirmed/likely, "
              f"{possible} possible")

    return 1 if confirmed else 0


if __name__ == "__main__":
    sys.exit(main())
