#!/usr/bin/env python3
"""link-guard: audit the links in a repo's Markdown files, check them live,
and name the ones that are dead -- before a reader finds them.

What it checks, per link:
  * relative file links -- does the file exist, on disk, next to the post?
  * #anchor links -- does the heading exist in the target file?
  * github.com tree/<branch>/ or blob/<branch>/ links -- does the branch
    still exist? If the branch is gone but the same path exists on main,
    the link is repointable: one sed away from working again.
  * external links -- HTTP HEAD (GET fallback), following redirects.
    403/429 are reported as BOT-WALL, not dead: many sites block scripts
    but serve browsers fine. Verify those by hand before calling them dead.

Usage:
  python3 link-guard.py audit <paths...> [--timeout 10] [--workers 8]
      [--json report.json] [--root DIR]

Exit code 0 when nothing is dead, 1 when any link is DEAD or BROKEN
(missing file, missing anchor, branch gone with no main equivalent,
HTTP 4xx/5xx). BOT-WALL, REDIRECT and UNKNOWN do not fail the run:
a transport failure is inconclusive, not a dead link -- the script
says so instead of guessing.

No dependencies beyond the Python standard library. No model calls.
"""
import argparse
import concurrent.futures
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "link-guard/1.0 (link audit; +https://sanoj.dev)"}

INLINE_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(\S+)", re.M)
REF_USE = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")
BARE_URL = re.compile(r"(?<![(\"'=])https?://[^\s<>\")\]]+")
HTML_LINK = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
FENCED = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`]*`")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
HEADING = re.compile(r"^#{1,6}\s+(.+)$", re.M)


def slugify(text):
    """GitHub-style heading anchor: lowercase, spaces to hyphens,
    drop punctuation except hyphens and underscores."""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text)


def strip_code(text):
    return INLINE_CODE.sub("", FENCED.sub("", text))


def extract_links(path):
    """Return [(url, line_no)] for every link in a Markdown file,
    skipping frontmatter, fenced code blocks and inline code."""
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    body = FRONTMATTER.sub("", raw, count=1)
    # line numbers must survive code stripping, so work line by line
    # for the code-aware patterns and on the stripped body for the rest.
    links = []
    lines = body.split("\n")
    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        clean = INLINE_CODE.sub("", line)
        for m in INLINE_LINK.finditer(clean):
            links.append((m.group(2), i))
        for m in IMAGE_LINK.finditer(clean):
            links.append((m.group(2), i))
        for m in HTML_LINK.finditer(clean):
            links.append((m.group(1), i))
    stripped = strip_code(body)
    refs = dict(REF_DEF.findall(stripped))
    for m in REF_USE.finditer(stripped):
        key = m.group(2) or m.group(1)
        if key in refs:
            # line number of the use, not the definition
            line_no = stripped[:m.start()].count("\n") + 1
            links.append((refs[key], line_no))
    for m in BARE_URL.finditer(stripped):
        url = m.group(0).rstrip(".,;:")
        line_no = stripped[:m.start()].count("\n") + 1
        links.append((url, line_no))
    return links


def headings_of(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return set()
    return {slugify(h) for h in HEADING.findall(text)}


def check_site_link(url, root):
    """A link like /blog/<slug>/ or /boring/: an address on the published
    site, not a file in the repo. /blog/<slug>/ is live when some post
    folder holds <slug>.md; /boring/ is the plain page; / is the home page."""
    path = url.split("#")[0].rstrip("/")
    if path in ("", "/boring"):
        target = "apps/plain/index.html" if path == "/boring" else "apps/plain/index.html"
        return ("OK", "site root / plain page") if os.path.exists(
            os.path.join(root, target)) else ("BROKEN", "plain page missing")
    m = re.match(r"^/blog/([^/]+)$", path)
    if m:
        slug = m.group(1)
        for dirpath, _, names in os.walk(os.path.join(root, "content", "blog")):
            if f"{slug}.md" in names:
                return ("OK", f"post {slug} exists")
        return ("BROKEN", f"no post with slug {slug}")
    return ("SKIP", f"site path {path} -- not checked against the repo")


def check_relative(url, source_file, root):
    """A link like img/cover.png or ../other.md, resolved from its file."""
    if url.startswith("/"):
        return check_site_link(url, root)
    path, _, frag = url.partition("#")
    if not path:
        target = source_file
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(source_file), path))
    if not os.path.exists(target):
        return ("BROKEN", f"file does not exist: {os.path.relpath(target, root)}")
    if frag and target.endswith((".md", ".markdown")):
        if frag not in headings_of(target):
            return ("BROKEN", f"anchor #{frag} not found in {os.path.basename(target)}")
    return ("OK", "file exists")


def check_github_branch(url):
    """github.com/<owner>/<repo>/(tree|blob)/<branch>/... -- is the link
    alive? Branch names contain slashes (skill/log-triage), so the
    branch cannot be split from the path by eye: a link that 404s is
    diagnosed by checking the live branch list first (the branch may
    exist while the path is wrong), then by finding the longest trailing
    path that still exists on main. Returns a verdict tuple, or None
    when the link is not a branch link / not a 404 (the caller then
    checks it as an ordinary external link)."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/(tree|blob)/(.+)$", url)
    if not m:
        return None
    owner, repo, kind, remainder = m.groups()
    remainder = remainder.rstrip("/")
    status, _ = http_status(url)
    if status == 200:
        return ("OK", "200")
    if status not in (404, 410, None):
        return None  # 403/429 etc.: let the caller classify it (bot-wall)
    # The link 404s (or the host never answered). Is the branch alive?
    branches = github_branches(owner, repo)
    if branches is not None:
        live = [b for b in branches
                if remainder == b or remainder.startswith(b + "/")]
        if live:
            branch = max(live, key=len)
            rest = remainder[len(branch):]
            return ("BROKEN", f"branch '{branch}' exists but path "
                              f"'{rest or '/'}' does not (404)")
    # The branch is gone (or the branch list was unreachable): find the
    # longest trailing path that still exists on main, and repoint there.
    parts = remainder.split("/")
    for i in range(1, len(parts)):
        rest = "/" + "/".join(parts[i:])
        main_url = f"https://github.com/{owner}/{repo}/{kind}/main{rest}"
        s, _ = http_status(main_url)
        if s == 200:
            note = ("; the branch list was unreachable, so this repoint "
                    "is a best guess" if branches is None else "")
            return ("BROKEN", "branch link 404s -- the branch is gone; "
                               f"same path exists on main -> repoint to {main_url}{note}")
    main_url = f"https://github.com/{owner}/{repo}/{kind}/main"
    s, _ = http_status(main_url)
    if s == 200:
        return ("BROKEN", "branch link 404s -- the branch is gone; "
                           f"the repo root on main is {main_url}")
    return ("BROKEN", "branch link 404s and the path is not on main either")


_branch_cache = {}


def github_branches(owner, repo, timeout=10):
    """Live branch names for a public repo, via the GitHub API
    (unauthenticated: 60 requests/hour; one request per repo, cached).
    Returns None when the API is unreachable, so the caller falls back
    to the main-equivalent heuristic instead of failing."""
    key = (owner, repo)
    if key in _branch_cache:
        return _branch_cache[key]
    branches = None
    url = (f"https://api.github.com/repos/{owner}/{repo}"
           f"/branches?per_page=100")
    try:
        while url:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                branches = (branches or []) + [
                    b["name"] for b in json.load(r)]
                nxt = re.search(r'<([^>]+)>;\s*rel="next"',
                                r.headers.get("Link", ""))
                url = nxt.group(1) if nxt else None
    except Exception:
        branches = None
    _branch_cache[key] = branches
    return branches


def http_status(url, timeout=10):
    """HEAD, falling back to GET (some servers reject HEAD).
    A 4xx on HEAD is retried with GET before it counts: Hacker News
    answers HEAD with 405 for a page that serves fine on GET.
    A transport failure (reset, timeout) is retried once: some hosts
    drop the first connection from a script and answer the second.
    Returns (status_code_or_None, final_url_or_error)."""
    import time
    last_err = "unreachable"
    for attempt in range(2):
        for method in ("HEAD", "GET"):
            req = urllib.request.Request(url, headers=UA, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    if method == "HEAD" and r.status == 204:
                        continue  # "I will not show you this" (YouTube watch
                        # pages sometimes answer HEAD with 204): retry with GET
                    return (r.status, r.geturl())
            except urllib.error.HTTPError as e:
                if method == "HEAD" and e.code in (400, 401, 403, 405):
                    continue  # HEAD refused; the page may still serve on GET
                return (e.code, e.geturl() if hasattr(e, "geturl") else url)
            except (urllib.error.URLError, TimeoutError, ValueError,
                    http.client.HTTPException, OSError) as e:
                last_err = str(e)
                if method == "HEAD":
                    continue
                break  # transport failure on GET: retry the whole attempt
        else:
            continue  # HEAD+GET both fell through without a verdict
        time.sleep(2)
    return (None, last_err)


def check_external(url, timeout=10):
    branch = check_github_branch(url)
    if branch is not None:
        return branch
    # GitHub's list pages (stargazers, forks, watchers) are JS-rendered and
    # answer 404 to plain HTTP clients while serving fine in a browser --
    # verified 2026-11-27: torvalds/linux/stargazers 404s to curl too.
    if re.match(r"https://github\.com/[^/]+/[^/]+/"
                r"(stargazers|network/members|watchers|forks)/?$", url):
        return ("BOT-WALL", "GitHub list page; 404s to scripts, serves in a browser")
    status, info = http_status(url, timeout)
    if status is None:
        return ("UNKNOWN", f"no response after retry: {info}")
    if status == 200:
        return ("OK", "200")
    if status in (301, 302, 303, 307, 308):
        return ("REDIRECT", f"{status} -> {info}")
    if status in (403, 429):
        return ("BOT-WALL", f"{status} -- site blocks scripts; verify in a browser")
    if 500 <= status < 600:
        # A 5xx says the server is struggling right now, not that the
        # page is gone: GitHub answers 503 when it rate-limits anonymous
        # requests, and the same URL answers 200 minutes later. Calling
        # that BROKEN would be a false alarm, so it is UNKNOWN instead.
        return ("UNKNOWN", f"HTTP {status} -- server error; retry later")
    if 400 <= status < 600:
        return ("BROKEN", f"HTTP {status}")
    return ("BROKEN", f"HTTP {status}")


def audit(paths, root, timeout=10, workers=8):
    """Walk the given files/dirs, extract links, check each once.
    Returns (results, summary) where results is a list of dicts."""
    md_files = []
    for p in paths:
        if os.path.isdir(p):
            for dirpath, _, names in os.walk(p):
                for n in sorted(names):
                    if n.endswith((".md", ".markdown")):
                        md_files.append(os.path.join(dirpath, n))
        elif os.path.isfile(p):
            md_files.append(p)
    # collect unique (url, source file) pairs, keeping first line number
    seen = {}
    for f in sorted(md_files):
        for url, line in extract_links(f):
            if url.startswith(("mailto:", "tel:", "#")):
                continue
            seen.setdefault((url, f), line)
    jobs = sorted(seen.items())  # ((url, file), line)

    def check_one(job):
        (url, source), line = job
        rel_source = os.path.relpath(source, root)
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme in ("http", "https"):
            verdict, detail = check_external(url, timeout)
            kind = "external"
        elif parsed.scheme == "":
            verdict, detail = check_relative(url, source, root)
            kind = "relative"
        else:
            verdict, detail = ("SKIP", f"scheme {parsed.scheme}")
            kind = "other"
        return {"url": url, "file": rel_source, "line": line,
                "kind": kind, "verdict": verdict, "detail": detail}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(check_one, jobs):
            results.append(r)
    summary = {}
    for r in results:
        summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1
    summary["total"] = len(results)
    summary["files"] = len(md_files)
    return results, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit Markdown links in a repo.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="check every link under the given paths")
    a.add_argument("paths", nargs="+")
    a.add_argument("--timeout", type=int, default=10)
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--json", default=None)
    a.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    if args.cmd == "audit":
        root = os.path.abspath(args.root)
        import time
        t0 = time.time()
        results, summary = audit(args.paths, root, args.timeout, args.workers)
        summary["seconds"] = round(time.time() - t0, 1)
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump({"summary": summary, "results": results}, f, indent=2)
        for r in results:
            if r["verdict"] in ("BROKEN", "BOT-WALL", "REDIRECT", "UNKNOWN"):
                print(f"{r['verdict']:9} {r['file']}:{r['line']}  {r['url']}")
                print(f"{'':9} {r['detail']}")
        print()
        print(f"files: {summary['files']}  links: {summary['total']}  "
              + "  ".join(f"{k}: {v}" for k, v in sorted(summary.items())
                          if k not in ("total", "files")))
        dead = summary.get("BROKEN", 0)
        return 1 if dead else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
