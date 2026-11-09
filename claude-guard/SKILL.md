---
name: claude-guard
description: Audit a repo for secrets Claude Code's "Don't Ask Again" saved into settings files, and fix them. Use when the user asks to check whether their Claude Code approvals leaked credentials, to scan a repo for secrets in .claude/settings.local.json or .claude/settings.json, or after reading about the Apiiro research (Nov 2026) that found 2,539 secrets in 1,994 public repos. Scans locally, never contacts a host, never tries a credential, and never prints a full secret.
---

# Guard your Claude Code settings against secret leaks

When you approve a shell command in Claude Code with "Yes, and don't ask
again", Claude Code saves the exact command as an allow rule in
`.claude/settings.local.json`. If that command held a password or a key,
the secret now sits in plain text inside your project. Security firm
Apiiro found 1,122 public copies of that file on GitHub holding real
secrets (research, November 5, 2026), and 215 of them were missed by
both gitleaks and TruffleHog — because a password typed inside a
command (`PGPASSWORD=...`, `sshpass -p ...`) does not look like a known
key format. This skill finds exactly those, and fixes them.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python "$S/scan.py" <project>     # audit
python "$S/fix.py" <file> --apply # clean up, after rotating
```

Tools: Python 3.10+, git. No packages, no network, no credentials tried.

## 1. Scan

Run the scanner on the project (or on one settings file):

```bash
python "$S/scan.py" .                # human-readable report
python "$S/scan.py" . --json         # machine-readable report
python "$S/scan.py" . --transcripts  # also scan saved agent transcripts
```

It finds `.claude/settings.local.json` and `.claude/settings.json`,
checks every `permissions.allow` / `deny` / `ask` rule, `env` value and
hook command for secrets, and for each file reports three git facts:
tracked, present in git history, and covered by `.gitignore` or the
global excludes. Findings are `confirmed` (a known key format, or a
password inside a URL), `likely` (a password typed into a command),
or `possible` (a long mixed-case string — review by hand). Values are
shown redacted, first four characters and last two, so the report is
safe to paste into a ticket. Exit code 1 means a confirmed or likely
secret was found.

## 2. Read the report before touching anything

The order matters, and getting it wrong is the one way to make this
worse. A secret that was ever committed is public from the moment it
was pushed; deleting the file does not un-publish it, and old copies
stay in git history and in forks. So:

1. **Rotate first.** Change every password, token and key the scan
   found, starting with the ones paired with a public server — those
   are the ones that give access. The redacted previews and locations
   tell you which credentials to rotate.
2. **Then clean up.** Only after rotation, run the fixer.
3. **Then verify.** Re-run the scanner: it must report zero
   confirmed/likely secrets.

If the file was never committed anywhere, rotation is still the safe
default when you cannot prove it stayed local — but say so, and let
the user decide.

## 3. Fix

```bash
python "$S/fix.py" .claude/settings.local.json          # dry run first
python "$S/fix.py" .claude/settings.local.json --apply   # clean the file
```

The fixer removes every rule with a confirmed or likely secret (the whole rule: a rule
that embeds a password cannot be made safe by editing the password
out), blanks secret `env` values, removes hook commands that embed a
secret, keeps a timestamped backup next to
the file, adds `.claude/settings.local.json` to the project's own
`.gitignore`, and re-scans the cleaned file to prove it is clean. Rules
it can only call "possible" are left in place and flagged for review by
hand. For
each removed rule it prints a safe replacement — a wildcard pattern
such as `Bash(psql *)`, or the same command with the secret as an
environment variable, such as `Bash(psql $DATABASE_URL *)`. The backup still holds the secrets: keep it
off git and delete it once rotation is done.

After rotation, untrack the file:

```bash
python "$S/fix.py" .claude/settings.local.json --apply --after-rotation
```

That runs `git rm --cached` on the file. If the file was ever pushed,
purge it from history too — the fixer prints the `git filter-repo`
command; coordinate the force-push with your team, because it rewrites
shared history.

## 4. Stop it happening again

Tell the user the three habits that prevent the next leak:

- **Approve patterns, not commands.** `Bash(npm run *)` instead of
  `Bash(npm run build --token=...)`. A rule with no `*` matches one
  exact command — including the secret typed into it.
- **Pass secrets as variables, not values.** `$DATABASE_URL` in the
  command, the value in the environment or a secrets manager. A saved
  rule then holds the variable name, not the secret.
- **Put the local file in the project's `.gitignore`.** Claude Code
  adds it to your *global* git excludes when it creates the file —
  that protection lives on one machine, in one user's git settings,
  and does nothing for a file that was already committed, a fork, or
  a teammate's clone. The project's own `.gitignore` travels with
  the project.

## 5. Org-wide check

For a whole organisation, the same file can be found on GitHub with
code search for the filename `settings.local.json` (and
`settings.json`), plus a history search per repository — Apiiro's
research found secrets in git history that no current copy holds.
Treat `.claude/`, `.cursor/`, `.gemini/` and `.specstory/` — Apiiro's
list, plus `.codex/` — and agent
transcript folders as holding secrets, the same way you treat `.env`
files: add them to pre-commit and CI secret scanning, including
history, and make sure the scanner catches passwords inside commands,
not only known key formats.

## Honest limits

- The scanner recognises formats and patterns; it cannot tell whether
  a credential is still live, and it never tries one. "Found" means
  exposed, not "known to be exploited".
- Passwords that look like ordinary words are the hardest case: the
  scanner flags the command patterns (`PGPASSWORD=`, `sshpass -p`,
  `--password`), but a password hidden in an unusual flag may need a
  human eye. The `possible` findings are for that.
- A password containing a `$` is treated as an environment-variable
  reference and skipped — the safe form — so a literal `$` in a real
  password is a known blind spot; check those rules by hand.
- The scanner reads settings files and, with `--transcripts`, saved
  agent transcripts. It does not scan your whole disk, your shell
  history, or other tools' files. Those are separate checks.
