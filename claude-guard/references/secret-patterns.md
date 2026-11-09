# Secret patterns claude-guard recognises

All examples below are fake. A pattern is only a finding when the
value is not a placeholder (`***`, `your-password`, `changeme`), not
an environment-variable reference (`$DATABASE_URL`), and not an
obvious example (`AKIAIOSFODNN7EXAMPLE`).

## Known key formats — severity: confirmed

These are the formats ordinary secret scanners already catch. They
are included so one scan covers everything, not because they are
hard to find.

| Pattern | Example (fake) |
|---|---|
| AWS access key | `AKIAIOSFODNN7EXAMPLE` |
| GitHub token | `ghp_` + 36 characters |
| npm token | `npm_` + 36 characters |
| Anthropic key | `sk-ant-api03-…` |
| Stripe live key | `sk_live_…` |
| Slack token | `xoxb-…` |
| Private key | `-----BEGIN PRIVATE KEY-----` |
| JWT | `eyJ…​.eyJ…​.…` |

## Passwords inside commands — severity: likely

This is the class that matters. Apiiro ran gitleaks and TruffleHog
over the 1,122 files with a real secret: gitleaks flagged 564,
TruffleHog 643, and **neither flagged 215**. Most misses were
passwords typed inside commands — a password after `PGPASSWORD=` or
`sshpass -p` looks like an ordinary word in an ordinary command line,
and no key format matches it.

| Pattern | Example (fake) |
|---|---|
| `PGPASSWORD=<value>` | `PGPASSWORD=hunter2-fake psql …` |
| `MYSQL_PWD=<value>` | `MYSQL_PWD=hunter2-fake mysql …` |
| `sshpass -p <value>` | `sshpass -p hunter2-fake ssh …` |
| `mysql -p<value>` | `mysql -phunter2-fake …` |
| `--password=<value>` / `--password <value>` | `--password hunter2-fake` |
| `--token=<value>` / `--api-key=<value>` | `--token abc123-fake` |
| `Authorization: Bearer|Basic <value>` | `Authorization: Bearer abc123-fake` |
| `curl -u <user>:<pass>` | `curl -u deploy:deploy-pass-fake …` |
| Password in a URL | `postgres://app:db-pass-fake@db.example.internal:5432/appdb` |

## Possible — severity: possible, review by hand

A long (24+ character) mixed-case string inside a quoted value or
after `=` that matches no known format. It could be a token, or a
long label. The scanner cannot tell, so it flags it and lets a human
decide. These never change the exit code on their own.

## Known blind spots

- A password containing a `$` is treated as an environment-variable
  reference (`$VAR`) and skipped. A literal `$` in a real password
  would be missed; check rules containing `$` by hand if you are
  unsure whether the value is a variable or a literal.
- A password hidden behind an unusual flag the patterns do not list
  (for example a tool-specific `--auth` spelling) is missed. The
  `possible` findings and a manual read of the file are the backstop.
- The scanner does not validate credentials — it never contacts a
  host — so it cannot say whether a found secret is still live.
