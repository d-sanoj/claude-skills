# Link-guard

Audit the links in a repo's Markdown files before a reader finds the dead ones.

Wednesday, November 25: I clicked a link in one of my own blog posts and got a 404. I checked all of them — 24 posts, 165 external links, 23 dead. Every one pointed at a GitHub branch I had deleted after merging its pull request. The link was alive when I wrote the post and dead the day the branch went away. Two days later I re-audited with this script: 365 links, 1 dead — and zero branch links left, because the fix (repoint everything at `main`) held. The one dead link was external: a news-aggregator article, published November 11, gone by November 27.

Out of 24 dead links found across the two audits, 23 were self-inflicted. That is what this skill is for. The full story is in the blog post ["Link rot is mostly self-inflicted"](https://sanoj.dev/blog/link-rot-is-self-inflicted/) (November 27, 2026).

Original work, built from the author's own two audits and from the literature: Pew Research Center's ["When Online Content Disappears"](https://www.pewresearch.org/wp-content/uploads/sites/20/2024/05/pl_2024.05.17_link-rot_report.pdf) (2024) for the background rate, Zittrain, Albert and Lessig's ["Perma"](https://ia600100.us.archive.org/16/items/permascopingandaddressingtheproblemoflinkandreferencerotinlegaldocuments/SSRN-id2329161.pdf) (Harvard Law Review Forum, 2014) for link rot vs reference rot, Ahrefs' [link rot study](https://ahrefs.com/blog/link-rot-study/) for the web-scale numbers, and GitHub's docs on [deleting branches in a pull request](https://docs.github.com/en/enterprise-server@3.11/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/deleting-and-restoring-branches-in-a-pull-request) for the deletion mechanism.

## Install

Copy this folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project):

```bash
cp -r link-guard ~/.claude/skills/
```

Requires Python 3.10+. Standard library only — no packages, no network beyond the links themselves, no model calls.

## Quick start

1. Audit — check every link under the paths you give it:

```bash
python3 scripts/link-guard.py audit content/blog README.md --root .
```

```text
BROKEN    content/blog/blog-10-11-11-2026/is-opus-5-5-nerfed.md:152  https://aicoder.com/news/news-20261107-x-discussion-opus-5-5-nerf-debate-1400-claude-code-sessions-theo-reasoning-summarizer
          HTTP 404
BOT-WALL  content/blog/blog-8-11-09-2026/claude-code-dont-ask-again-leak.md:6  https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again
          403 -- site blocks scripts; verify in a browser

files: 26  links: 365  BOT-WALL: 6  BROKEN: 1  OK: 358
```

(First two flagged lines of the real run — the run lists all six bot walls.)

Exit code 1 when anything is BROKEN, 0 otherwise. Bot walls, redirects and unknowns don't fail the run.

2. Fix — a dead branch link is one word: the branch name becomes `main`, the path stays. The script prints the repoint for you:

```text
BROKEN    index.md:10  https://github.com/d-sanoj/claude-skills/tree/skill/log-triage/log-triage
          branch link 404s -- the branch is gone; same path exists on main -> repoint to https://github.com/d-sanoj/claude-skills/tree/main/log-triage
```

A dead external link has no automatic fix — find a replacement source or remove the citation.

3. Re-run — confirm the count line reads `BROKEN: 0` (or that BROKEN is absent). Put the audit in CI on every push: rot from deletion is instant, so a check on every push finds one dead link while you still remember writing it.

## What it checks

| Verdict | Meaning |
| --- | --- |
| OK | HTTP 200, file exists, anchor exists |
| REDIRECT | Redirects are followed silently, so a redirect reports OK — listed for completeness, never fires |
| BOT-WALL | 403/429, or a page that 404s to scripts but serves browsers — verify by hand |
| UNKNOWN | Host never answered (DNS, timeout, reset after retry), or a server error (5xx) — inconclusive, not dead |
| BROKEN | Server said no (404, other 4xx), file missing, anchor missing, branch gone |

- **Relative links** resolve against the file that contains them, on disk; `#fragment` anchors are checked against the target file's headings.
- **Site links** (`/blog/<slug>/`, `/boring/`) resolve against the repo layout.
- **GitHub branch links** are diagnosed against the repo's live branch list (GitHub API, one request per repo, cached): branch alive but path wrong, or branch gone with a repoint to the same path on `main`.
- **External links** get HEAD, then GET when HEAD is refused (Hacker News answers HEAD with 405; YouTube's HEAD answers vary — 204 sometimes, 200 others), then one retry after a pause when the connection drops. A transport failure after retry is UNKNOWN, never BROKEN.

What counts as a link: inline, reference-style, bare URLs, images, HTML `href`/`src`. What doesn't: URLs in frontmatter, fenced code blocks, or inline code.

## Try it

`examples/fixture/` is a six-link demo — a good file, a missing file, a missing anchor, a genuinely deleted branch, a live page, and a URL inside a code block that is not a link:

```bash
cd examples/fixture
python3 ../../scripts/link-guard.py audit . --root .
```

It prints three BROKEN lines, including the repoint. `tests/run_skill_tests.py` runs 23 checks (mostly offline; the one live test checks the real deleted branch and skips without a network).

## The rules

1. **Link repos at `main` only, never at a branch.** A branch is a work-in-progress address.
2. **Check after every merge, in CI if you can.**
3. **Verify a bot wall once in a browser and move on.** Don't delete a live link because a script got a 403.

## What it cannot tell you

Whether a link still points at what you *meant*. A page can return 200 with entirely different content than the day you linked it — that is reference rot, and it needs a human, or an archive.
