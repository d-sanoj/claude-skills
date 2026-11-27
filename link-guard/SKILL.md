---
name: link-guard
description: Audit the links in a repo's Markdown files before a reader finds the dead ones. Use when a pull request merges (its branch is about to be deleted), when a post or doc page links to a GitHub branch, when you want to know whether your docs' links still work, or after any link fix to prove it held. Extracts every link (inline, reference, bare, image, HTML), skips code samples and frontmatter, checks relative links and anchors on disk, resolves site links against the repo layout, diagnoses GitHub branch links against the live branch list with a repoint to main, and classifies external links as OK, REDIRECT, BOT-WALL, UNKNOWN or BROKEN -- with a script that does the mechanical part deterministically.
---

# Link-guard: the link was alive when you wrote it

Wednesday, November 25. I clicked a link in one of my own blog posts and got a 404. I checked all of them: 24 posts, 165 external links, 23 dead. Fourteen percent, and the posts were just over three weeks old. Every one of the 23 pointed at a GitHub branch I had deleted after merging its pull request. The link was alive when I wrote the post and dead the day the branch went away — which, in my workflow, is usually the day the post goes up, because I link to the thing while its PR is still open and delete the branch when it merges.

A link to a file on a branch looks permanent. It has the same shape as any other GitHub URL, it works when you test it, and nothing about it says "this expires." What expires is the branch. GitHub lets anyone with write access delete the head branch of a merged pull request, and once the branch is gone, every URL containing its name 404s. The files are not gone; they are on `main`, one path segment away. The link is dead anyway, because the URL names the branch, not the content.

```bash
S="${CLAUDE_SKILL_DIR}/scripts"
python3 "$S/link-guard.py" audit content/blog README.md --root .
python3 "$S/link-guard.py" audit docs/ --root . --json report.json
```

Tools: Python 3.10+. Standard library only, no packages, no network beyond the links themselves, no model calls. Exit code 1 when anything is BROKEN, 0 otherwise.

## The measurement behind it

Two audits, two days apart, on the author's own blog and skills repo. The first audit (November 25) found the problem; the second (November 27) proved the fix held:

| Audit | Links | Dead | Of which branch links |
| --- | --- | --- | --- |
| Blog, Nov 25 (24 posts) | 165 external | 23 (14%) | 23 — every one |
| Blog, Nov 27 (25 posts + README) | 365 total, 181 unique external | 1 | 0 of 23 GitHub `tree/`/`blob/` links |
| Skills repo, Nov 27 (42 files) | 30 external, 23 unique | 0 | 0 |

The 23 dead links broke down as 9 skill folders on their PR branches (21 occurrences across 10 posts) and one experiment folder on its branch (2). Zero pointed at other people's sites. Two more links were repointed in the same fix before they could die — the flake-hunt skill, linked at its branch in that morning's post, whose branch was still alive (it still is). The fix repointed 25 links in total: 23 dead, 2 pre-emptive. The one dead link in the second audit was external: a news-aggregator article cited in the November 11 post, published November 11, 404 by November 27 — sixteen days. It 404s to `curl`, to the checker, and to a browser fetch, while the site's homepage answers 200: the article is gone, not hiding.

Counting note: the November 25 audit counted raw occurrences; the November 27 audit counts each (URL, file) pair once — 23 GitHub file links, 34 raw mentions, all on `main`. And the skills-repo audit printed 2 BROKEN lines (`LICENSE` and `runtime/OFL.txt` in the motion-reel folder) that are artifacts of auditing a partial download — only the `.md` files were fetched, so two real files looked missing. Both exist in the repo; no external link there is dead.

The background rate, for scale: Pew Research Center (2024) found 38% of webpages from 2013 gone a decade later and a quarter of all pages from 2013–2023 gone; Zittrain, Albert and Lessig (2014) found more than 70% of URLs in three Harvard law journals and 50% of URLs in US Supreme Court opinions no longer produce the information originally cited. My blog's links are three weeks old and mostly point at GitHub, arXiv and documentation — the most stable addresses on the web — so 1 dead in 181 is the right order of magnitude for young links to stable hosts. The rate is a property of *your* links, not of links in general, and the only way to know yours is to measure them. The full story, with the bot-wall taxonomy below, is in the blog post ["Link rot is mostly self-inflicted"](https://sanoj.dev/blog/link-rot-is-self-inflicted/) (November 27, 2026).

## 1. Audit: check every link once

```bash
cd <your-repo>
python3 "$S/link-guard.py" audit content/blog README.md --root .
```

```text
BROKEN    content/blog/blog-10-11-11-2026/is-opus-5-5-nerfed.md:152  https://aicoder.com/news/news-20261107-x-discussion-opus-5-5-nerf-debate-1400-claude-code-sessions-theo-reasoning-summarizer
          HTTP 404
BOT-WALL  content/blog/blog-8-11-09-2026/claude-code-dont-ask-again-leak.md:6  https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again
          403 -- site blocks scripts; verify in a browser

files: 26  links: 365  BOT-WALL: 6  BROKEN: 1  OK: 358
```

(First two flagged lines of the real run — the run lists all six bot walls.)

The audit walks the paths you give it, extracts every link, and checks each unique (URL, file) pair once. The whole run above took 17 seconds for 365 links (8 workers, the default). Pass `--json report.json` for a machine-readable report with one record per link: URL, file, line, kind, verdict, detail.

What counts as a link: inline `[text](url)`, reference-style `[text][ref]` plus its definition, bare URLs, images, and HTML `href`/`src`. What does not count: URLs in frontmatter, in fenced code blocks, or in inline code — a URL in a code sample is not a link, and counting it would be a false positive of its own. See `tests/fixtures/extractor.md` for the exact cases.

## 2. Read the verdicts

| Verdict | Meaning | Fails the run? |
| --- | --- | --- |
| OK | HTTP 200, file exists, anchor exists | No |
| REDIRECT | Redirects are followed silently, so a redirect reports OK — listed for completeness, never fires | No |
| BOT-WALL | 403/429, or a page that 404s to scripts but serves browsers | No — verify by hand |
| UNKNOWN | Host never answered (DNS, timeout, reset after retry), or a server error (5xx) | No — inconclusive, not dead |
| BROKEN | Server said no (404, other 4xx), file missing, anchor missing, branch gone | **Yes** |

Bot walls, redirects and unknowns don't fail the run, because a run that fails on things you can't fix trains you to ignore it. The verdicts exist because real links taught the script each one:

- **Hacker News answers HEAD with 405.** Nine HN links came back "dead" on the first version, which used HEAD only. HN refuses HEAD requests; the pages serve fine on GET. The script retries with GET when HEAD is refused (400, 401, 403, 405). A checker that only uses HEAD will mislabel every HN link on the internet.
- **YouTube's HEAD answers vary.** One watch link returned 204 to HEAD in a HEAD-only run and 200 when re-checked with `curl` minutes later; GET is rate-limited intermittently (429 on one run, 200 on the next). The script retries with GET when HEAD comes back 204, and treats 429 as a bot wall, not a death. Bot-wall verdicts flicker; re-run before acting on one.
- **GitHub's own list pages 404 to scripts.** The README links to the repo's stargazers page, which answers 404 to `curl` — and to the same request for `torvalds/linux`, so it is not about the repo. The page serves in a browser; GitHub's list pages are JavaScript-rendered. The script special-cases `/stargazers`, `/watchers`, `/forks` and `/network/members`. Verify a special case by hand before adding it: a rule you add to make a red light go away is how a checker stops checking.
- **Some hosts drop the connection, then answer 403 on retry.** The script retries a transport failure once; a failure after retry is UNKNOWN, never BROKEN — an inconclusive check must not be reported as a dead link. A server error (5xx) is UNKNOWN for the same reason: GitHub answered 503 for eleven links during one run and 200 for all of them minutes later.

## 3. Branch links: the diagnosis that matters

This is the verdict the skill exists for. A GitHub `tree/<branch>/…` or `blob/<branch>/…` link 404s for two different reasons, and the fix is different for each:

- **The branch is gone.** The branch was deleted after its PR merged. The script finds the longest trailing path that still exists on `main` and prints the repoint: `tree/skill/log-triage/log-triage` → `tree/main/log-triage`.
- **The branch is alive but the path is wrong.** A typo in the folder name, a file that moved. The script says so by name, using the repo's live branch list from the GitHub API (one request per repo, cached; if the API is unreachable it falls back to the repoint heuristic and says so).

Branch names contain slashes (`skill/log-triage`), so the branch can't be split from the path by eye. The script does not try: it asks the API which branches exist, and for a deleted branch it tries the longest trailing path first. Two things I got wrong at first, and the script now handles: branches don't die *at* the merge, they die when someone deletes them — nine of my ten skill branches are gone, the tenth (`skill/flake-hunt`) is still there because I haven't deleted it yet — so a branch link is alive until it isn't, and only a check tells you which.

## 4. Fix, then re-run

The fix for a dead branch link is one word: the branch name becomes `main`, the path stays. The fix for a dead external link is a replacement source or a removed citation — there is no automatic repoint, and inventing one would be worse than the 404. After fixing, re-run the audit on the same paths and confirm the count line reads `BROKEN: 0` (or that BROKEN is absent). The exit code is your CI gate: put the audit in CI on every push, because rot from deletion is instant — a quarterly audit finds three months of dead links at once, while a check on every push finds one, while you still remember writing it.

## What the checker cannot tell you

It cannot tell you whether a link still points at what you *meant*. A page can return 200 with entirely different content than the day you linked it — Zittrain's study calls that reference rot, and it is the larger problem: of the Supreme Court links that still loaded, only 76% still led to the material cited. A status checker catches link rot. Content drift needs a human, or an archive.

## Rules that cover nearly all of it

1. **Link repos at `main` only, never at a branch.** A branch is a work-in-progress address. The moment you treat it as a permanent address, you have set a timer you can't see.
2. **Check after every merge, in CI if you can.** Rot from deletion is instant, so check on every push, not once a quarter.
3. **Verify a bot wall once in a browser and move on.** Don't "fix" it by deleting a live link, and don't teach the checker to ignore a whole host because one page annoyed you.
