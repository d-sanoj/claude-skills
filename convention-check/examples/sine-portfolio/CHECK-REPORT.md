# Checker report — sine-portfolio (its own conventions)

Command:

```
python3 check_conventions.py --rules conventions.json --root . <all 94 JS files>
```

Run 2026-11-15 against the conventions extracted the same day.

apps/designer/app/model/exportData.js:1 [JS-NAME] file 'exportData.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/designer/app/model/glyphFit.js:1 [JS-NAME] file 'glyphFit.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/measure/app/services/measurePage.js:1 [JS-NAME] file 'measurePage.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/portraits/app/services/fitPortrait.js:1 [JS-NAME] file 'fitPortrait.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/portraits/app/services/lineArt.js:1 [JS-NAME] file 'lineArt.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/site/app/model/Letter.js:1 [JS-NAME] PascalCase file 'Letter.js' does not define a class named Letter; use kebab-case
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
apps/site/app/services/pageLoader.js:1 [JS-NAME] file 'pageLoader.js' is camelCase; this repo uses kebab-case (except a file defining one class, which takes the class's PascalCase name)
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
scripts/lib/blog.js:285 [JS-DECL] uses var: var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:286 [JS-DECL] uses var: var figs = [].slice.call(document.querySelectorAll('figure.anim'));
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:288 [JS-DECL] uses var: var img = fig.querySelector('img[data-animated-src]');
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:289 [JS-DECL] uses var: var svg = fig.querySelector('svg');
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:290 [JS-DECL] uses var: var btn = fig.querySelector('.anim-control');
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:308 [JS-DECL] uses var: var btn = fig.querySelector('.anim-control');
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:400 [JS-DECL] uses var: var KEY = 'sanoj-home';
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:401 [JS-DECL] uses var: var root = __ROOT__;
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:402 [JS-DECL] uses var: var boring = __BORING__;
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:407 [JS-DECL] uses var: var v = prefer();
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
scripts/lib/blog.js:408 [JS-DECL] uses var: var href = v === 'plain' ? boring : root;
    repo evidence: const 1821 of 2187 declarations (83%); let 355, var 11
src/widgets/loader/model/Timeline.js:1 [JS-NAME] PascalCase file 'Timeline.js' does not define a class named Timeline; use kebab-case
    repo evidence: kebab 57, PascalCase 30 — 28 of the PascalCase files define a class of the same name
convention-check: 19 violation(s) in 9 file(s) (+95 advisory)

Advisory quote notes (121 before comment filtering, 95 after) are listed in the full output, not here — they do not fail the check.
