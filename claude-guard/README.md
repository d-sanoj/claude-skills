# claude-guard

Find the secrets Claude Code's "Don't Ask Again" saved into your
project, and fix them — before they end up on GitHub.

When you approve a shell command in Claude Code with "Yes, and don't
ask again", Claude Code saves the exact command as an allow rule in
`.claude/settings.local.json`. If that command held a password or a
key, the secret now sits in plain text inside your project. Security
firm Apiiro found 1,122 public copies of that file on GitHub holding
real secrets (research, November 5, 2026) — and 215 of them were
missed by both gitleaks and TruffleHog, because a password typed
inside a command does not look like a known key format. This skill
finds exactly those.

## Install

```bash
cp -r claude-guard ~/.claude/skills/        # every project
# or: cp -r claude-guard <project>/.claude/skills/   # one project
```

## Use it

```bash
python ~/.claude/skills/claude-guard/scripts/scan.py .
python ~/.claude/skills/claude-guard/scripts/fix.py .claude/settings.local.json --apply
```

The scanner reports every secret it finds (redacted — first four
characters, last two), whether the file is tracked by git, present in
git history, and covered by `.gitignore`. The fixer removes
secret-bearing rules, keeps a timestamped backup, adds the file to the
project's `.gitignore`, and prints a safe replacement rule for each
one it removed. Rules it can only call "possible" are left in place
and flagged for review by hand.

**Rotate first, then clean up.** A secret that was ever committed is
public from the moment it was pushed; deleting the file does not
un-publish it. Rotate every credential the scan found, then run the
fixer with `--after-rotation` to untrack the file.

## Test it

```bash
python ~/.claude/skills/claude-guard/scripts/test_scan.py
```

Builds a temporary git repo with fake secrets, commits the leaky file,
and checks the scanner finds them, reports the git exposure honestly,
and that the fixer removes them and stops the leak recurring. All
checks pass on the author's machine (37 checks). Every secret in the
tests and examples is fake.

## What it checks

| Check | Why it matters |
|---|---|
| Known key formats (AWS, GitHub, npm, Anthropic, Stripe, Slack, JWT, private keys) | The secrets ordinary scanners catch |
| Passwords inside commands (`PGPASSWORD=`, `MYSQL_PWD=`, `sshpass -p`, `mysql -p`, `--password`, `curl -u`, `Authorization:`) | The 215 files gitleaks and TruffleHog both missed |
| Passwords embedded in URLs (`postgres://user:pass@host`) | The most common database leak |
| `env` values and hook commands in the settings files | Secrets hide outside allow rules too |
| Tracked by git? In git history? Ignored? | The three facts that decide whether a leak happened |
| `--transcripts`: saved agent transcripts | The research found secrets in chat logs too |

## Limits

- The scanner cannot tell whether a credential is still live, and it
  never tries one. "Found" means exposed, not "known to be
  exploited".
- A password containing a `$` is treated as an environment-variable
  reference and skipped; check those rules by hand.
- It scans Claude Code settings files (and, with `--transcripts`,
  saved transcripts). It does not scan your whole disk, shell history,
  or other tools' files.

## Attribution

Original work, written for this repo. The motivation and the numbers
come from Apiiro's research "Coding Agents Are Leaking Your Secrets
to GitHub" (Shmulik Cohen and Matan Giladi, November 5, 2026):
https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again
— no code or text was taken from it. The mechanism is documented in
Anthropic's own Claude Code docs:
https://code.claude.com/docs/en/settings and
https://code.claude.com/docs/en/permissions.
