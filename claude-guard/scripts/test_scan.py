#!/usr/bin/env python3
"""End-to-end test for claude-guard: scan.py + fix.py on a real git repo.

Builds a temporary repo with a leaky settings file (FAKE secrets only),
commits it, and asserts the scanner finds the secrets, reports the git
exposure honestly, and that the fixer removes them and stops the leak
from recurring. Run: python test_scan.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "scan.py")
FIX = os.path.join(HERE, "fix.py")

LEAKY = {
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "permissions": {
        "allow": [
            "Bash(npm run *)",
            "Bash(PGPASSWORD=hunter2-fake psql -h db.example.internal "
            "-U app -d appdb -c 'SELECT 1')",
            "Bash(aws s3 ls s3://my-bucket --profile default)",
            "Bash(curl -u deploy:deploy-pass-fake $API_BASE/health)",
            "Bash(git log *)",
        ],
        "deny": ["Bash(rm -rf *)"],
    },
    "env": {"DATABASE_URL":
            "postgres://app:db-pass-fake@db.example.internal:5432/appdb"},
}

CLEAN = {
    "permissions": {
        "allow": ["Bash(npm run *)", "Bash(psql $DATABASE_URL -c *)"],
        "deny": ["Bash(rm -rf *)"],
    }
}

FAILS = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {extra}" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def run(args, cwd=None):
    return subprocess.run([sys.executable] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def sh(args, cwd):
    out = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                         timeout=30)
    assert out.returncode == 0, f"{args} failed: {out.stderr}"
    return out.stdout.strip()


def main():
    tmp = tempfile.mkdtemp(prefix="claude-guard-test-")
    try:
        repo = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(repo, ".claude"))
        sh(["git", "init", "-q"], repo)
        sh(["git", "config", "user.email", "test@example.invalid"], repo)
        sh(["git", "config", "user.name", "Test"], repo)

        # --- leaky file, committed (the realistic case) ---
        leaky_path = os.path.join(repo, ".claude", "settings.local.json")
        with open(leaky_path, "w") as fh:
            json.dump(LEAKY, fh, indent=2)
        sh(["git", "add", "."], repo)
        sh(["git", "commit", "-qm", "add leaky settings"], repo)

        out = run([SCAN, repo, "--json"], cwd=repo)
        data = json.loads(out.stdout)
        res = data["results"][0]
        check("scan finds the leaky file", len(data["results"]) == 1)
        classes = {f["class"] for f in res["findings"]}
        check("finds PGPASSWORD password", "pgpassword" in classes, str(classes))
        check("finds curl -u credential", "curl-user" in classes, str(classes))
        check("finds password in DATABASE_URL", "credential-url" in classes, str(classes))
        check("exit code 1 when secrets found", out.returncode == 1,
              f"got {out.returncode}")
        check("reports file as tracked", res["git"]["tracked"] is True)
        check("reports file in history", res["git"]["in_history"] is True)
        check("reports file not ignored", res["git"]["ignored"] is False)
        check("no full secret in output",
              "hunter2-fake" not in out.stdout
              and "deploy-pass-fake" not in out.stdout
              and "db-pass-fake" not in out.stdout)
        check("redacted preview present",
              any(f["value_preview"] == "hunt…ke"
                  for f in res["findings"]),
              json.dumps([f["value_preview"] for f in res["findings"]]))

        # --- dry run changes nothing ---
        before = open(leaky_path).read()
        out = run([FIX, leaky_path], cwd=repo)
        check("fix dry run exits 0", out.returncode == 0)
        check("dry run changes nothing", open(leaky_path).read() == before)
        check("dry run names the removed rules",
              "PGPASSWORD" in out.stdout and "curl -u" in out.stdout)
        check("dry run suggests psql without the secret",
              "Bash(psql *)" in out.stdout, out.stdout)
        check("dry run prints no full secret",
              "hunter2-fake" not in out.stdout
              and "deploy-pass-fake" not in out.stdout
              and "db-pass-fake" not in out.stdout)
        check("dry run suggests env-var form for curl rule",
              "Bash(curl $API_BASE *)" in out.stdout, out.stdout)

        # --- apply the fix ---
        out = run([FIX, leaky_path, "--apply"], cwd=repo)
        check("fix --apply exits 0", out.returncode == 0, out.stderr)
        after = json.load(open(leaky_path))
        rules = after["permissions"]["allow"]
        check("secret rules removed",
              all("PGPASSWORD" not in r and "curl -u" not in r for r in rules),
              str(rules))
        check("clean rules kept", "Bash(npm run *)" in rules
              and "Bash(git log *)" in rules)
        check("env secret blanked", after["env"]["DATABASE_URL"] == "")
        backups = [f for f in os.listdir(os.path.join(repo, ".claude"))
                   if f.startswith("settings.local.json.bak-")]
        check("backup written", len(backups) == 1, str(backups))
        gitignore = open(os.path.join(repo, ".gitignore")).read()
        check(".gitignore gains the entry",
              ".claude/settings.local.json" in gitignore, gitignore)

        # --- re-scan is clean, and untracking works ---
        out = run([SCAN, repo, "--json"], cwd=repo)
        data = json.loads(out.stdout)
        check("re-scan finds no confirmed secret",
              data["summary"]["confirmed_or_likely"] == 0,
              json.dumps(data["summary"]))
        check("re-scan exits 0", out.returncode == 0, f"got {out.returncode}")
        out = run([FIX, leaky_path, "--apply", "--after-rotation"], cwd=repo)
        code, _ = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--",
             ".claude/settings.local.json"],
            cwd=repo, capture_output=True, text=True).returncode, None
        check("file untracked after --after-rotation", code != 0)

        # --- a clean repo scans clean ---
        clean_repo = os.path.join(tmp, "clean")
        os.makedirs(os.path.join(clean_repo, ".claude"))
        sh(["git", "init", "-q"], clean_repo)
        with open(os.path.join(clean_repo, ".claude",
                               "settings.local.json"), "w") as fh:
            json.dump(CLEAN, fh, indent=2)
        out = run([SCAN, clean_repo, "--json"], cwd=clean_repo)
        check("clean repo exits 0", out.returncode == 0,
              f"got {out.returncode}: {out.stdout}")

        # --- a secret hiding in a hook command is cleaned too ---
        hook_repo = os.path.join(tmp, "hooks")
        os.makedirs(os.path.join(hook_repo, ".claude"))
        sh(["git", "init", "-q"], hook_repo)
        hook_path = os.path.join(hook_repo, ".claude", "settings.json")
        with open(hook_path, "w") as fh:
            json.dump({"hooks": {"PreToolUse": [{"hooks": [
                {"type": "command",
                 "command": "curl -u admin:admin-pass-fake "
                            "https://hooks.example.internal/ping"},
                {"type": "command", "command": "echo ok"}]}]}},
                fh, indent=2)
        out = run([SCAN, hook_repo, "--json"], cwd=hook_repo)
        check("hook secret is flagged by scan", out.returncode == 1,
              out.stdout)
        out = run([FIX, hook_path, "--apply"], cwd=hook_repo)
        check("fix removes the hook secret", out.returncode == 0, out.stderr)
        after = json.load(open(hook_path))
        kept = after["hooks"]["PreToolUse"][0]["hooks"]
        check("secret hook removed, clean hook kept",
              len(kept) == 1 and kept[0]["command"] == "echo ok",
              json.dumps(kept))
        out = run([SCAN, hook_repo, "--json"], cwd=hook_repo)
        check("hook repo re-scans clean", out.returncode == 0, out.stdout)
        check("no .gitignore entry for a shared settings file",
              not os.path.exists(os.path.join(hook_repo, ".gitignore")))

        # --- a possible-only finding is kept and flagged, not deleted ---
        poss_repo = os.path.join(tmp, "possible")
        os.makedirs(os.path.join(poss_repo, ".claude"))
        sh(["git", "init", "-q"], poss_repo)
        poss_path = os.path.join(poss_repo, ".claude", "settings.local.json")
        with open(poss_path, "w") as fh:
            json.dump({"permissions": {"allow": [
                "Bash(deploy --build-id='aB3dE5fG7hJ9kL2mN4pQ6rS8tU')"]}},
                fh, indent=2)
        out = run([SCAN, poss_repo, "--json"], cwd=poss_repo)
        data = json.loads(out.stdout)
        check("possible-only finding does not fail the scan",
              out.returncode == 0
              and data["summary"]["possible"] == 1, out.stdout)
        out = run([FIX, poss_path, "--apply"], cwd=poss_repo)
        after = json.load(open(poss_path))
        check("possible-only rule is kept, not deleted",
              after["permissions"]["allow"] == [
                  "Bash(deploy --build-id='aB3dE5fG7hJ9kL2mN4pQ6rS8tU')"],
              json.dumps(after))
        check("possible-only rule is flagged for review",
              "REVIEW BY HAND" in out.stdout, out.stdout)

        # --- bundled examples behave as labelled ---
        ex = os.path.join(HERE, "..", "examples")
        out = run([SCAN, os.path.join(ex, "leaky-settings.local.json"),
                   "--json"])
        data = json.loads(out.stdout)
        check("example leaky file flags 4 secrets",
              data["summary"]["confirmed_or_likely"] == 4,
              json.dumps(data["summary"]))
        check("example leaky file includes the AWS key",
              any(f["class"] == "aws-access-key"
                  for r in data["results"] for f in r["findings"]))
        out = run([SCAN, os.path.join(ex, "clean-settings.local.json"),
                   "--json"])
        check("example clean file is clean", out.returncode == 0,
              out.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{len(FAILS)} failure(s)" if FAILS else "\nAll checks passed.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
