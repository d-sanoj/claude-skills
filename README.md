# Claude Skills

A collection of Claude skills I build and improve. Each folder is one skill, with its own README and everything needed to install it.

## Skills

- **Claude Motion for Pro** — [motion-reel](motion-reel): animated explainers on any Claude Code plan, even though Claude Motion itself is Team/Enterprise only. First skill in this repo.
- **Claude Code secret-leak guard** — [claude-guard](claude-guard): audit a repo for secrets Claude Code's "Don't Ask Again" saved into settings files, and fix them. Second skill in this repo.
- **Model regression watcher** — [nerf-watch](nerf-watch): a frozen 8-task suite that scores your coding agent week to week, so when a model "feels nerfed" you have a number instead of a vibe. Third skill in this repo.
- **Test prover** — [prove-the-tests](prove-the-tests): make your coding agent prove its tests can fail — expected values from the requirement, red first, then a mutation check that deliberately breaks the code. Fourth skill in this repo.
- **Convention checker** — [convention-check](convention-check): make your coding agent write code that looks like yours — extract the conventions the repo already follows, measured with counts, and check the diff against them. Fifth skill in this repo.
- **Output evaluator** — [output-eval](output-eval): judge a generative model by its outputs, not its loss curve — a fixed three-gate rubric, 50 fixed-seed samples, and a scorer that tracks good% across runs. Sixth skill in this repo.
- **Commit crafter** — [commit-craft](commit-craft): make your coding agent write commits like a senior engineer — one logical change per commit, a subject under 72 characters, a body under five lines, no tool credit, and a checker that gates the commit instead of trusting a line in CLAUDE.md. Seventh skill in this repo.
- **Log triager** — [log-triage](log-triage): find the real cause of a failing build before fixing anything — first real error, traceback as one unit, summaries are not causes — with a script that does the mechanical part. Eighth skill in this repo.
- **Scope guard** — [scope-guard](scope-guard): keep your coding agent inside the scope it declared — a declared scope, a baseline, and a checker that gates the diff instead of trusting a line in CLAUDE.md. Ninth skill in this repo.
- **Flake hunter** — [flake-hunt](flake-hunt): find the flaky test before it eats your morning — run the suite N times, name every test that changed its answer, isolate each suspect alone, and quarantine what it finds. Tenth skill in this repo.

## Install

Each skill folder has its own README with install steps. In general: copy the skill folder into `~/.claude/skills/` (every project) or `<project>/.claude/skills/` (one project).

## License

Each skill folder carries its own license and attribution. Skills adapted from someone else's work say so in their README.
