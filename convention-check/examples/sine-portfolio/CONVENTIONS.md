# Conventions — sine-portfolio

Extracted by `extract_conventions.py` from what the code actually does. Every rule carries its count; a pattern below 80% is listed as mixed, not enforced.

Measured: 94 JS/TS files, 8,018 lines; 1 Python files, 233 lines.

## Rules

- **JS-DECL — declarations: const** (repo). const 1821 of 2187 declarations (83%); let 355, var 11. var survives only as listed outliers, if any.
- **JS-QUOTES — quotes: single** (repo). single quotes 2425 of 2654 (91%). The other quote style is allowed inside a string that contains the dominant quote character. The double quotes that remain cluster in HTML template strings and regexes, so this rule is advisory: the checker reports it but does not fail on it. Quote style is a formatter's job. [advisory — reported, does not fail the check]
- **JS-SEMI — semicolons: semicolons** (repo). 4078 lines end with ';' (92% of statement lines). Line-based checks are too noisy for this one — enforce it with a formatter, not the checker. [enforced by a formatter, not the checker]
- **JS-NAME — file naming: kebab-case, except a file defining one class takes that class's PascalCase name** (repo). kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name. Files whose names a framework dictates (e.g. _middleware.js) are exempt.
- **JS-NOLOG — logging: no console.log** (apps). 0 console.log calls across the whole directory; console.warn appears 2 time(s). Progress output belongs in scripts/, not shipped code.
- **JS-NOLOG — logging: no console.log** (functions). 0 console.log calls across the whole directory. Progress output belongs in scripts/, not shipped code.
- **JS-NOLOG — logging: no console.log** (src). 0 console.log calls across the whole directory. Progress output belongs in scripts/, not shipped code.
- **JS-ESM — modules: ESM import/export, no require()** (repo). 212 import statements, 0 require() calls. 
- **GIT-MSG — commit messages: Area: summary** (repo). 35 of 37 non-merge commits carry an Area: prefix (95%); top areas: Blog 25, Loader 5, Add blog post 2. Merge commits are exempt.

## Measured, but mixed — decide, don't enforce

- Error handling in `apps/`: throw 4, return_null 15, console_error 1.
- Error handling in `scripts/`: throw 79, return_null 15, console_error 10, process_exit 7.
- Error handling in `src/`: return_null 9.
- Logging in `apps/`: console_warn 2.
- Logging in `scripts/`: console_log 25, console_warn 4.
- Logging in `server/`: console_log 5.
- `var` outliers (the only places `var` appears): scripts/lib/blog.js (11). Record each as a deliberate exception or fix it.

## Layout

- Check scripts: scripts/check-a11y.js, scripts/check-blog.js, scripts/check-compact.js.
- Commit messages: 35 of 37 non-merge commits carry an `Area:` prefix.

## What this does not cover

- Intent. A check can say the file is named right and uses `const`; it cannot say the change is correct.
- Conventions that live only in review culture. If the measurement is mixed, a human decides — the extractor does not guess.
