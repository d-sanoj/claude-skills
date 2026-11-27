# Fixture doc

A link that works: [the good file](good-file.md).

A link to a file that was never written: [the missing file](missing-file.md).

A link to a heading that does not exist: [nowhere in the good file](good-file.md#no-such-heading).

A link to a GitHub branch that was deleted when its pull request merged:
[log-triage on its old branch](https://github.com/d-sanoj/claude-skills/tree/skill/log-triage/log-triage).
The same folder on main is alive:
[log-triage on main](https://github.com/d-sanoj/claude-skills/tree/main/log-triage).

A link to a live page: [the author's blog](https://sanoj.dev/blog/).

A link inside `code with https://example.com/not-a-link` is not a link,
and neither is one in a fenced block:

```text
see https://example.com/also-not-a-link for details
```
