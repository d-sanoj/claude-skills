# Before / after: the Chrome log

A real CI log from the author's site (GitHub Actions run 44135960638, November 17, 2026). The build step failed. The log is 185 lines; the only line containing the word "error" is the generic exit line.

## Before: read the bottom

The last lines of the log:

```text
CI  Build  2026-11-17T17:21:24.3824096Z Chrome did not open a debugging port
CI  Build  2026-11-17T17:21:24.3989741Z ##[error]Process completed with exit code 1.
```

Reading bottom-up, the agent sees `Process completed with exit code 1` and concludes the build step failed — which says nothing about why. The usual next move is to re-read the build script looking for a bug, or to "fix" the exit code. There is no bug in the change: every earlier step (checkout, install, blog check) passed. The failure is Chrome never opening a debugging port — environmental in character, a flaky launcher rather than a bug in the change. The fix, [PR #29](https://github.com/d-sanoj/sine-portfolio/pull/29) the same day, hardened the launcher itself: install Chrome for Testing, let Chrome pick the debug port, wait up to 60 seconds, retry up to three times.

## After: the skill's verdict

```bash
python3 scripts/triage-log.py build.log
```

```text
ROOT CAUSE: Chrome did not open a debugging port
STEP:       Build
COMMAND:    node scripts/build.js --dist
CLASS:      environment
NEXT:       rerun first: if it passes, it was the environment, not your change.
```

The script found no error line in the failing step, so by R4 it took the step's last substantive line — the process's last words before it died. The class says environment, so the first step is a rerun: if it passes, it was the environment, not the change. When the flake kept biting, the launcher was hardened instead — which is what PR #29 did the same day.

## The same pattern, three more times

The author's own CI failed the same way three mornings running (November 18, 19, 20) — a different cause each time in form, the same shape in substance. The blog check failed with:

```text
BlogError: content/blog/blog-17-11-18-2026/chunk-by-section-not-by-word-count.md:
  image "img/cover.png" was not found at content/blog/blog-17-11-18-2026/img/cover.png
```

The `.md` was committed before the images (a two-commit upload), so the check ran on a commit where the cover did not exist yet. Grepping the first "error" finds this one — it is the only error line — but reading the bottom finds only the generic exit line. The script's verdict:

```text
ROOT CAUSE: BlogError: ... image "img/cover.png" was not found at .../img/cover.png
FILE:       content/blog/blog-17-11-18-2026/chunk-by-section-not-by-word-count.md
STEP:       UNKNOWN STEP
COMMAND:    node scripts/check-blog.js
REPEATS:    same error 2x in this log
CLASS:      config
```

Config, not defect: the fix is to finish the upload, not to edit the post. The same failure, the same verdict, three days running — and each time the fix was the next commit, not a code change.
