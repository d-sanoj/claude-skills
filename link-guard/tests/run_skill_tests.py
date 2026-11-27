#!/usr/bin/env python3
"""Tests for link-guard. Run from this folder:

    python3 run_skill_tests.py

Most tests are offline: they exercise the extractor and the relative-link
checker on fixtures/ only. One live test checks a real deleted GitHub
branch; it prints SKIP when there is no network instead of failing.
"""
import importlib.util
import os
import subprocess
import sys
import urllib.request

_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scripts", "link-guard.py")
_spec = importlib.util.spec_from_file_location("link_guard", _SCRIPT)
link_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(link_guard)

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "link-guard.py")
FIXTURES = os.path.join(HERE, "fixtures")
PASSED = 0


def check(name, cond, extra=""):
    global PASSED
    assert cond, f"FAIL: {name} {extra}"
    PASSED += 1
    print(f"  ok: {name}")


def test_extractor_skips_code_and_frontmatter():
    links = dict()
    for url, line in link_guard.extract_links(
            os.path.join(FIXTURES, "extractor.md")):
        links.setdefault(url, line)
    check("inline link found", "https://example.com/inline" in links)
    check("image link found", "img/cover.png" in links)
    check("reference link resolved", "https://example.com/ref" in links)
    check("bare URL found", "https://example.com/bare" in links)
    check("frontmatter URL skipped",
          "https://example.com/frontmatter" not in links)
    check("inline-code URL skipped",
          "https://example.com/not-a-link" not in links)
    check("fenced-code URL skipped",
          "https://example.com/also-not-a-link" not in links)


def test_relative_links():
    root = os.path.join(FIXTURES, "audit")
    src = os.path.join(root, "doc.md")
    v, _ = link_guard.check_relative("present.md", src, root)
    check("present file is OK", v == "OK")
    v, _ = link_guard.check_relative("absent.md", src, root)
    check("missing file is BROKEN", v == "BROKEN")
    v, _ = link_guard.check_relative("present.md#real-heading", src, root)
    check("present anchor is OK", v == "OK")
    v, _ = link_guard.check_relative("present.md#no-such-heading", src, root)
    check("missing anchor is BROKEN", v == "BROKEN")


def test_site_links():
    # Site-absolute links are resolved against the repo layout, not the disk.
    root = os.path.join(FIXTURES, "audit")
    v, d = link_guard.check_site_link("/blog/present-post/", root)
    check("existing post slug is OK", v == "OK", d)
    v, _ = link_guard.check_site_link("/blog/no-such-post/", root)
    check("missing post slug is BROKEN", v == "BROKEN")
    v, _ = link_guard.check_site_link("/boring/", root)
    check("/boring/ is OK when the plain page exists", v == "OK")


def test_heading_slug():
    check("slugify drops punctuation",
          link_guard.slugify("Hello, World! (2026)") == "hello-world-2026")
    check("slugify keeps hyphens",
          link_guard.slugify("well-known fact") == "well-known-fact")


def test_audit_fixture_offline():
    # Audit a directory whose links are all relative: no network needed.
    audit_dir = os.path.join(FIXTURES, "audit")
    r = subprocess.run([sys.executable, SCRIPT, "audit", audit_dir,
                        "--root", audit_dir, "--workers", "2"],
                       capture_output=True, text=True)
    check("audit exits 1 when a link is broken", r.returncode == 1)
    check("audit names the missing file",
          "absent.md" in r.stdout and "BROKEN" in r.stdout)
    check("audit names the missing anchor",
          "no-such-heading" in r.stdout)
    check("audit reports the count line",
          "links: 5" in r.stdout)


def test_deleted_branch_live():
    # A real deleted branch: skill/log-triage was deleted after PR #8
    # merged; the same folder is alive on main. Skip without network.
    try:
        verdict, detail = link_guard.check_github_branch(
            "https://github.com/d-sanoj/claude-skills/tree/skill/log-triage/log-triage")
    except Exception as e:  # network down, DNS failure, proxy block
        print(f"  SKIP (live): deleted-branch check, no network ({e})")
        return
    check("deleted branch is BROKEN", verdict == "BROKEN", detail)
    check("report points at main", "tree/main/log-triage" in detail)
    try:
        status, _ = link_guard.http_status(
            "https://github.com/d-sanoj/claude-skills/tree/main/log-triage")
    except Exception as e:
        print(f"  SKIP (live): main-equivalent check, no network ({e})")
        return
    check("main equivalent answers 200", status == 200, f"got {status}")


def main():
    print("link-guard tests")
    test_extractor_skips_code_and_frontmatter()
    test_relative_links()
    test_site_links()
    test_heading_slug()
    test_audit_fixture_offline()
    test_deleted_branch_live()
    print(f"{PASSED} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
