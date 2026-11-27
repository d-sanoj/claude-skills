# Before / after: the two audits

The worked example for link-guard. Same checker, two days apart, on the
author's blog (repo `d-sanoj/sine-portfolio`).

## Before — Wednesday, November 25, 2026

All 24 posts on the site, 165 external links. The audit was a one-off
script that day; the numbers are from the run log:

```text
links checked: 165 external
dead: 23 (14%)
```

| What the dead links pointed at | Dead links |
| --- | --- |
| Skill folders on their PR branches (`tree/skill/<name>/…`) | 21 occurrences, 9 skills, 10 posts |
| An experiment folder on its PR branch | 2 |
| Links to other people's sites | 0 |

Every dead link was self-inflicted: a GitHub branch deleted after its
pull request merged. Fix: repoint all 23 dead links at `main` (blog PR #40, merged
the same day), and adopt the rule — link repos at `main` only. Two more
links were repointed in the same PR before they could die: the flake-hunt
skill, linked at its branch in that morning's post, whose branch was still
alive (it still is). The PR repointed 25 links in total: 23 dead, 2 pre-emptive.

## After — Friday, November 27, 2026

Same checker, now `scripts/link-guard.py`. 25 posts plus the README:

```text
BROKEN    content/blog/blog-10-11-11-2026/is-opus-5-5-nerfed.md:152  https://aicoder.com/news/news-20261107-x-discussion-opus-5-5-nerf-debate-1400-claude-code-sessions-theo-reasoning-summarizer
          HTTP 404
BOT-WALL  content/blog/blog-8-11-09-2026/claude-code-dont-ask-again-leak.md:6  https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again
          403 -- site blocks scripts; verify in a browser

files: 26  links: 365  BOT-WALL: 6  BROKEN: 1  OK: 358
```

(First two flagged lines — the run lists all six bot walls.)

- 365 links in 17 seconds. 186 external occurrences (181 unique),
  179 relative links, all fine.
- 23 GitHub `tree/`/`blob/` links, all at `main`. The fix held.
- The one dead link is external: an AICoder article cited in the
  November 11 post, published November 11, 404 by November 27.
  Confirmed 404 by `curl`, by the checker, and by a browser fetch,
  while the site's homepage answers 200.

Second corpus, same day — the skills repo (42 Markdown files):

```text
files: 42  links: 43  BOT-WALL: 1  BROKEN: 2  OK: 40
```

The 2 BROKEN are an artifact of auditing a partial download (only the
`.md` files were fetched, so `LICENSE` and `runtime/OFL.txt` look
missing — they exist in the repo). External links only: 30 occurrences,
23 unique, 29 OK, 1 bot-wall (the same apiiro article), 0 dead.

Across both corpora: 185 unique external links, 1 dead. Out of 24 dead
links found in the two audits, 23 were self-inflicted.
