# Fixtures

Two deliberately bad files and one advisory-only file, used by
`tests/run_skill_tests.py`. Each bad one breaks conventions the
fixture repo's extractor found, so the checker must fail on it with
exactly the violations listed. The advisory-only file passes, with
a note.

- `bad-service.js` — 2 × `JS-DECL` (`var` instead of `const`) and
  1 × `JS-NOLOG` (`console.log` in `apps/` code), plus 1 advisory
  `JS-QUOTES` note for its double-quoted string. Its header comment
  *describes* the violations, which also regression-tests that the
  checker skips comment-only lines.
- `DateHelpers.js` — 1 × `JS-NAME`: a PascalCase file that defines
  no class of that name, so it should be kebab-case
  (`date-helpers.js`).
- `ok-but-quoted.js` — clean by every hard rule, with one
  double-quoted string. Advisory only: the checker reports it and
  still exits 0.
