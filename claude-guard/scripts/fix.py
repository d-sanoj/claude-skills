#!/usr/bin/env python3
"""Fix Claude Code settings files that scan.py flagged.

Order matters, and this script enforces it:

1. ROTATE FIRST. A secret that was ever committed is public the moment
   it was pushed, and deleting the file does not un-publish it. Rotate
   every credential the scan found, then clean up. This script writes a
   rotation checklist (redacted values, exact locations) and refuses to
   touch git history until you confirm rotation with --after-rotation.
2. Then clean the file: secret-bearing allow rules are removed (the
   whole rule, because a rule that embeds a password cannot be made
   safe by editing the password out — the command would not run the
   same way), a backup is kept next to the file, and the cleaned file
   is re-scanned to prove it is clean.
3. Then stop it happening again: `.claude/settings.local.json` is added
   to the project's own .gitignore (the protection Claude Code adds
   lives in your global git excludes, which does not travel with the
   project and does nothing for a file that was already committed).

Usage:
    python fix.py <settings-file> [--apply] [--after-rotation]
    python fix.py --scan <directory> [--apply] [--after-rotation]

Without --apply this is a dry run: it prints exactly what it would do
and changes nothing. --after-rotation additionally runs
`git rm --cached` on files that are tracked. It never rewrites git
history: purging a secret from history needs git filter-repo and a
force-push, and the script prints the exact commands for that instead.

The script never prints a full secret value.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan as scanner


def git(args, cwd):
    try:
        out = subprocess.run(["git"] + args, cwd=cwd,
                             capture_output=True, text=True, timeout=30)
        return out.returncode, out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, ""


ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=[^\s]+$")
WRAPPERS = {"export", "env", "sudo", "command", "time", "nice"}


def suggest_replacement(rule):
    """A safe pattern rule to replace a removed exact-command rule.

    Leading VAR=value assignments are stripped first: they are where
    the secret usually hides (PGPASSWORD=..., MYSQL_PWD=...), and
    suggesting them back would put the secret straight into the file
    again. Wrappers such as `export` get no suggestion — any pattern
    for them would be too broad to be safe.
    """
    m = re.match(r"Bash\((.+)\)\s*$", rule)
    if not m:
        return None
    cmd = m.group(1).strip()
    tokens = cmd.split()
    while tokens and ASSIGN.match(tokens[0]):
        tokens.pop(0)
    if not tokens:
        return None
    first = tokens[0]
    if first in WRAPPERS:
        return None
    var = re.search(r"\$[A-Z_][A-Z0-9_]*", cmd)
    if var:
        return (f"Bash({first} {var.group(0)} *)",
                "pass the secret as an environment variable, "
                "not inside the command")
    return (f"Bash({first} *)",
            "approve the command family with a wildcard instead of "
            "one exact command that embeds a secret")


def clean_file(path, dry_run):
    """Remove rules with a confirmed or likely secret. Returns (report, changed).

    Rules whose only findings are "possible" are left in place and
    reported for review by hand — a long string the scanner cannot
    identify is not proven to be a secret. Hook commands are cleaned
    the same way as allow rules: a hook that embeds a secret is
    removed, not kept. The report always carries a post-fix re-scan
    (or, for a dry run, the findings the fixer cannot remove), so a
    file that is still dirty is never reported as clean.
    """
    result = scanner.scan_settings_file(path)
    if result.get("error"):
        return {"path": path, "error": result["error"]}, False
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    perms = data.get("permissions") or {}
    removed = []
    possible_only = []
    suggestions = []
    for section in ("allow", "deny", "ask"):
        kept = []
        for rule in perms.get(section) or []:
            if not isinstance(rule, str):
                kept.append(rule)
                continue
            hits = scanner.find_secrets(rule, section)
            hard = [h for h in hits
                    if h["severity"] in ("confirmed", "likely")]
            if hard:
                removed.append({
                    "section": section, "rule": rule,
                    "findings": [{"class": h["class"],
                                  "severity": h["severity"],
                                  "value_preview": h["value_preview"]}
                                 for h in hard],
                })
                sug = suggest_replacement(rule) if section == "allow" else None
                if sug:
                    suggestions.append({"removed": rule,
                                        "suggested": sug[0],
                                        "why": sug[1]})
            else:
                if hits:
                    possible_only.append({
                        "section": section, "rule": rule,
                        "findings": [{"class": h["class"],
                                      "severity": h["severity"],
                                      "value_preview": h["value_preview"]}
                                     for h in hits],
                    })
                kept.append(rule)
        if section in perms:
            perms[section] = kept
    # Secrets hiding in env values or hook commands: blank the value,
    # never keep a secret in a file the user is about to keep.
    env = data.get("env") or {}
    for key, value in list(env.items()):
        if isinstance(value, str):
            hits = scanner.find_secrets(value, key)
            hard = [h for h in hits
                    if h["severity"] in ("confirmed", "likely")]
            if hard:
                removed.append({
                    "section": f"env.{key}", "rule": value,
                    "findings": [{"class": h["class"],
                                  "severity": h["severity"],
                                  "value_preview": h["value_preview"]}
                                 for h in hard],
                })
                env[key] = ""
            elif hits:
                possible_only.append({
                    "section": f"env.{key}", "rule": value,
                    "findings": [{"class": h["class"],
                                  "severity": h["severity"],
                                  "value_preview": h["value_preview"]}
                                 for h in hits],
                })
    hooks = data.get("hooks") or {}
    for event, groups in hooks.items():
        group_list = groups if isinstance(groups, list) else [groups]
        for group in group_list:
            if not isinstance(group, dict):
                continue
            hook_entries = group.get("hooks") or []
            kept_hooks = []
            for hook in hook_entries:
                cmd = (hook or {}).get("command", "")
                if isinstance(cmd, str) and cmd:
                    hits = scanner.find_secrets(cmd, "hooks")
                    hard = [h for h in hits
                            if h["severity"] in ("confirmed", "likely")]
                    if hard:
                        removed.append({
                            "section": f"hooks.{event}", "rule": cmd,
                            "findings": [{"class": h["class"],
                                          "severity": h["severity"],
                                          "value_preview": h["value_preview"]}
                                         for h in hard],
                        })
                        continue
                    if hits:
                        possible_only.append({
                            "section": f"hooks.{event}", "rule": cmd,
                            "findings": [{"class": h["class"],
                                          "severity": h["severity"],
                                          "value_preview": h["value_preview"]}
                                         for h in hits],
                        })
                kept_hooks.append(hook)
            group["hooks"] = kept_hooks
    report = {"path": path, "removed": removed,
              "possible_only": possible_only, "suggestions": suggestions,
              "git": result["git"]}
    # Findings the fixer cannot remove on its own (anything outside
    # permissions/env/hooks, or a possible-only rule): surface them.
    covered = {f["value_preview"]
               for r in removed for f in r["findings"]}
    report["uncovered"] = [f for f in result["findings"]
                           if f["value_preview"] not in covered
                           and not any(f["value_preview"] == p["value_preview"]
                                       for r in possible_only
                                       for p in r["findings"])]
    if not removed and not dry_run:
        # Nothing to change, but still prove the file's state.
        report["still_flagged"] = [f for f in result["findings"]
                                   if f["severity"] in ("confirmed", "likely")]
        return report, False
    if dry_run:
        return report, bool(removed)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = f"{path}.bak-{stamp}"
    with open(backup, "w", encoding="utf-8") as fh:
        with open(path, encoding="utf-8") as src:
            fh.write(src.read())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    report["backup"] = backup
    # Prove the cleaned file is clean.
    after = scanner.scan_settings_file(path)
    report["still_flagged"] = [f for f in after["findings"]
                               if f["severity"] in ("confirmed", "likely")]
    return report, True


def ensure_gitignored(path, dry_run):
    """Add the local settings file to the project's own .gitignore.

    Only for settings.local.json. The shared settings.json is meant
    to be committed, so ignoring it would be wrong — secrets in that
    file must be removed, not hidden.
    """
    if os.path.basename(path) != "settings.local.json":
        return {"gitignore": None, "added": False,
                "reason": "shared settings file is meant to be "
                          "committed — remove the secrets instead"}
    root = scanner.repo_root(path)
    if root is None:
        return None
    ignore_path = os.path.join(root, ".gitignore")
    entry = ".claude/settings.local.json"
    existing = ""
    if os.path.exists(ignore_path):
        with open(ignore_path, encoding="utf-8") as fh:
            existing = fh.read()
    if entry in [line.strip() for line in existing.splitlines()]:
        return {"gitignore": ignore_path, "added": False,
                "reason": "already listed"}
    if dry_run:
        return {"gitignore": ignore_path, "added": True, "dry_run": True}
    with open(ignore_path, "a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(entry + "\n")
    return {"gitignore": ignore_path, "added": True}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", help="settings file to fix")
    ap.add_argument("--scan", metavar="DIR",
                    help="fix every flagged settings file under DIR")
    ap.add_argument("--apply", action="store_true",
                    help="make the changes (default is a dry run)")
    ap.add_argument("--after-rotation", action="store_true",
                    help="also run git rm --cached on tracked files; "
                         "only use this after rotating every secret")
    args = ap.parse_args(argv)

    if args.scan:
        files = scanner.find_settings_files(os.path.abspath(args.scan))
        files = [f for f in files
                 if scanner.scan_settings_file(f)["findings"]]
    elif args.path:
        files = [os.path.abspath(args.path)]
    else:
        ap.error("pass a settings file, or --scan <directory>")

    if not args.apply:
        print("DRY RUN — nothing will change. Add --apply to fix.\n")
    reports = []
    for path in files:
        report, changed = clean_file(path, dry_run=not args.apply)
        report["gitignore"] = ensure_gitignored(path,
                                                dry_run=not args.apply)
        if args.apply and args.after_rotation:
            g = report["git"]
            if g.get("tracked"):
                code, _ = git(["rm", "--cached", "--", path], g["repo"])
                report["untracked"] = code == 0
        reports.append(report)

    total_removed = sum(len(r.get("removed", [])) for r in reports)
    total_possible = sum(len(r.get("possible_only", [])) for r in reports)
    still_dirty = any(r.get("still_flagged") for r in reports)
    print(f"{len(reports)} file(s), {total_removed} secret-bearing "
          "rule(s) removed.\n")
    for r in reports:
        print(f"== {r['path']} ==")
        if r.get("error"):
            print(f"  ERROR: {r['error']}")
            continue
        if not r.get("removed"):
            print("  Nothing to remove.")
        for rem in r.get("removed", []):
            print(f"  REMOVED [{rem['section']}] "
                  f"{scanner.redact_text(rem['rule'][:100])}")
            for f in rem["findings"]:
                print(f"      {f['class']} ({f['severity']}): "
                      f"{f['value_preview']}")
        for pos in r.get("possible_only", []):
            print(f"  REVIEW BY HAND [{pos['section']}] "
                  f"{scanner.redact_text(pos['rule'][:100])}")
            for f in pos["findings"]:
                print(f"      {f['class']} ({f['severity']}): "
                      f"{f['value_preview']} — not proven to be a secret, "
                      "left in place")
        for sug in r.get("suggestions", []):
            print(f"  INSTEAD ADD: {sug['suggested']}")
            print(f"      ({sug['why']})")
        if r.get("backup"):
            print(f"  Backup: {r['backup']} — keep it off git; "
                  "it still holds the secrets.")
        if r.get("still_flagged"):
            print("  !! The cleaned file STILL flags secrets — "
                  "check it by hand before committing:")
            for f in r["still_flagged"]:
                print(f"      [{f['severity']}] {f['class']}: "
                      f"{f['meaning']} ({f['where']})")
        if r.get("uncovered") and not args.apply:
            print("  !! Findings this fixer cannot remove on its own "
                  "— fix by hand:")
            for f in r["uncovered"]:
                print(f"      [{f['severity']}] {f['class']}: "
                      f"{f['meaning']} ({f['where']})")
        gi = r.get("gitignore") or {}
        if gi.get("added"):
            print(f"  .gitignore: added .claude/settings.local.json "
                  f"({'dry run' if gi.get('dry_run') else 'done'})")
        elif gi.get("reason"):
            print(f"  .gitignore: {gi['reason']}")
        g = r.get("git") or {}
        if g.get("tracked"):
            print("  git: file is TRACKED.")
            if args.apply and args.after_rotation:
                print(f"  git rm --cached: "
                      f"{'done' if r.get('untracked') else 'FAILED'}")
            else:
                print("  After rotating the secrets, run:")
                print(f"    git rm --cached {r['path']}")
        if g.get("in_history"):
            print(f"  git: file is in history "
                  f"({g['history_commits']} commits) — deleting it "
                  "now does not remove old copies.")
            print("  To purge it from history (after rotating):")
            print("    git filter-repo --path "
                  ".claude/settings.local.json --invert-paths")
            print("    (coordinate the force-push with your team)")

    if total_removed:
        print("\nROTATE FIRST, then clean up:")
        print("  1. Rotate every credential listed above (the redacted "
              "values tell you which ones).")
        print("  2. Only then run fix.py --apply --after-rotation, or "
              "the git rm --cached command it prints.")
        print("  3. Re-run scan.py afterwards: it must report zero "
              "confirmed/likely secrets.")
    if total_possible:
        print(f"\n{total_possible} 'possible' item(s) left in place — "
              "review them by hand; the scanner cannot tell a token "
              "from a long label.")
    if still_dirty:
        print("\n!! Some file(s) still flag secrets after the fix. "
              "Do not commit them until the remaining findings are "
              "resolved by hand.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
